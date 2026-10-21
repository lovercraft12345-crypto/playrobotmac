"""Offline 3DS reader and native, mouse-controlled PCB viewer.

The exported board is displayed as geometry, never as live hardware telemetry.
"""
from __future__ import annotations

import math
import os
import struct
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from ui_theme import UI_FONT
from tkinter import ttk

import numpy as np
from PIL import Image, ImageDraw, ImageTk


class BoardModel:
    def __init__(self, path):
        data = Path(path).read_bytes()
        if len(data) < 6 or struct.unpack_from('<H', data)[0] != 0x4D4D:
            raise ValueError('El archivo no es un modelo 3DS válido.')
        materials, objects = {}, []

        def chunks(start, end):
            while start < end:
                if start + 6 > end:
                    raise ValueError('Modelo 3DS incompleto.')
                tag, size = struct.unpack_from('<HI', data, start)
                if size < 6 or start + size > end:
                    raise ValueError('Tamaño de sección 3DS inválido.')
                yield tag, start + 6, start + size
                start += size

        def string(pos, end):
            nul = data.find(b'\0', pos, end)
            if nul < 0:
                raise ValueError('Nombre de objeto incompleto.')
            return data[pos:nul].decode('latin1'), nul + 1

        def material(start, end):
            name, color = '', (165, 175, 185)
            for tag, a, b in chunks(start, end):
                if tag == 0xA000:
                    name, _ = string(a, b)
                elif tag == 0xA020:
                    for ctag, c, d in chunks(a, b):
                        if ctag in (0x0011, 0x0012):
                            color = tuple(data[c:c+3])
                        elif ctag in (0x0010, 0x0013):
                            color = tuple(max(0, min(255, round(v*255))) for v in struct.unpack_from('<3f', data, c))
            materials[name] = color

        def mesh(start, end, name):
            vertices, faces, groups = None, None, []
            for tag, a, b in chunks(start, end):
                if tag == 0x4110:
                    n = struct.unpack_from('<H', data, a)[0]
                    vertices = np.frombuffer(data, '<f4', n*3, a+2).reshape(-1, 3).copy()
                elif tag == 0x4120:
                    n = struct.unpack_from('<H', data, a)[0]
                    faces = np.frombuffer(data, '<u2', n*4, a+2).reshape(-1, 4)[:, :3].copy()
                    for sub, c, d in chunks(a+2+n*8, b):
                        if sub == 0x4130:
                            mat, pos = string(c, d)
                            count = struct.unpack_from('<H', data, pos)[0]
                            ids = np.frombuffer(data, '<u2', count, pos+2).copy()
                            groups.append((mat, ids))
            if vertices is not None and faces is not None:
                if not np.isfinite(vertices).all() or (len(faces) and faces.max() >= len(vertices)):
                    raise ValueError('Geometría inválida en el modelo.')
                objects.append((name, vertices, faces, groups))

        def walk(start, end):
            for tag, a, b in chunks(start, end):
                if tag in (0x4D4D, 0x3D3D):
                    walk(a, b)
                elif tag == 0xAFFF:
                    material(a, b)
                elif tag == 0x4000:
                    name, pos = string(a, b)
                    for sub, c, d in chunks(pos, b):
                        if sub == 0x4100:
                            mesh(c, d, name)

        walk(0, len(data))
        if not objects:
            raise ValueError('El modelo no contiene superficies.')
        all_vertices, all_faces, all_colors = [], [], []
        offset = 0
        self.object_names = []
        for name, vertices, faces, groups in objects:
            colors = np.full((len(faces), 3), 175, dtype=np.float64)
            for mat, ids in groups:
                if len(ids) and ids.max() >= len(faces):
                    raise ValueError('Material con caras inválidas.')
                colors[ids] = materials.get(mat, (165, 175, 185))
            all_vertices.append(vertices)
            all_faces.append(faces.astype(np.int32)+offset)
            all_colors.append(colors)
            self.object_names.append(name)
            offset += len(vertices)
        self.vertices = np.concatenate(all_vertices).astype(np.float64)
        self.faces = np.concatenate(all_faces)
        self.colors = np.concatenate(all_colors)
        self.bounds = np.array([self.vertices.min(axis=0), self.vertices.max(axis=0)])
        self.vertices -= self.bounds.mean(axis=0)
        span = np.ptp(self.vertices, axis=0).max()
        self.vertices /= max(span, 1e-9)
        triangles = self.vertices[self.faces]
        self._normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        self._normal_lengths = np.linalg.norm(self._normals, axis=1)
        # Preserve the major surfaces during drag instead of dropping every nth
        # triangle (which used to punch large holes through the board).
        cutoff = np.partition(self._normal_lengths, max(0, len(self.faces)-25000))[max(0, len(self.faces)-25000)]
        self._fast_indices = np.flatnonzero(self._normal_lengths >= max(cutoff, 1e-14))

    def render(self, width, height, yaw=0.0, tilt=0.6, zoom=1.0, fast=False, background='#eaf0f6'):
        """Orthographic painter renderer. Full model on release; reduced mesh while dragging."""
        width, height = max(1, int(width)), max(1, int(height))
        cy, sy, ct, st = math.cos(yaw), math.sin(yaw), math.cos(tilt), math.sin(tilt)
        # Board exports use XY as the PCB plane and Z as component height.
        rotation = np.array([[cy, -sy, 0], [sy*st, cy*st, -ct], [sy*ct, cy*ct, st]])
        transformed = self.vertices @ rotation.T
        ids = self._fast_indices if fast else slice(None)
        faces, colors = self.faces[ids], self.colors[ids]
        triangles = transformed[faces]
        normals = self._normals[ids] @ rotation.T
        lengths = self._normal_lengths[ids]
        light = np.array([-0.3, -0.5, 0.8]); light /= np.linalg.norm(light)
        brightness = 0.6 + 0.4*np.abs(normals @ light)/np.maximum(lengths, 1e-12)
        colors = np.clip((colors+12)*brightness[:, None], 0, 255).astype(np.uint8)
        scale = min(width, height)*0.81*zoom
        points = triangles[:, :, :2]*scale
        points[:, :, 0] += width/2
        points[:, :, 1] += height/2
        visible = (points[:, :, 0].max(axis=1)>=0) & (points[:, :, 0].min(axis=1)<width)
        visible &= (points[:, :, 1].max(axis=1)>=0) & (points[:, :, 1].min(axis=1)<height)
        visible &= lengths > 1e-14
        ids = np.flatnonzero(visible)
        order = ids[np.argsort(triangles[ids, :, 2].mean(axis=1))]
        image = Image.new('RGBA' if background is None else 'RGB', (width, height),
                          (0, 0, 0, 0) if background is None else background)
        draw = ImageDraw.Draw(image)
        for i in order:
            draw.polygon(tuple(map(tuple, points[i])), fill=tuple(colors[i]))
        return image


class BoardSurface(tk.Frame):
    def __init__(self, parent, model, compact=False):
        super().__init__(parent)
        self.compact = compact
        self._gpu = False
        self.model = model
        self.yaw, self.tilt, self.zoom = 0.0, 0.75, 1.0
        self._pending = None
        self._last_mouse = None
        self._image = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='placa-3d')
        self._future = None
        self._requested = None
        self._poll_id = None
        self._closed = False
        self.configure(bg='#f6f9fd')
        self._engine = tk.StringVar(value='Preparando vista…')
        if not compact:
            tk.Label(self, text='Explora tu placa', bg='white', fg='#172449',
                     font=(UI_FONT, 20, 'bold'), pady=15).pack(fill='x')
        toolbar = tk.Frame(self, bg='white', padx=8, pady=6)
        toolbar.pack(side='bottom', fill='x')
        actions = [('↺', self.reset), ('Arriba', self.top),
                   ('＋', lambda: self.change_zoom(1.15)), ('−', lambda: self.change_zoom(1/1.15))]
        for text, command in actions:
            tk.Button(toolbar, text=text, command=command, relief='flat', bg='#edf3fb',
                      fg='#172449', padx=9, pady=7, cursor='hand2').pack(side='left', padx=3)
        if not compact:
            tk.Label(toolbar, textvariable=self._engine, bg='white', fg='#63758a').pack(side='right', padx=8)
        self.viewport = tk.Frame(self, bg='#f6f9fd')
        self.viewport.pack(fill='both', expand=True)
        self._create_surface()
        self.bind('<Destroy>', self._on_destroy, add='+')
        self.schedule()

    def _create_surface(self):
        try:
            engine = os.getenv('PLAYROBOT_3D_ENGINE', 'auto').lower()
            if engine == 'software' or (engine == 'auto' and sys.platform != 'win32'):
                raise ImportError('Use compatible renderer on this platform')
            from board_gl import BoardGLCanvas
            self.canvas = BoardGLCanvas(self.viewport, self.model, self, self._use_software)
            self._gpu = True
            self._engine.set('Vista 3D acelerada')
        except Exception:
            self.canvas = tk.Canvas(self.viewport, width=260, height=250, bg='#f6f9fd', highlightthickness=0)
            self._engine.set('Vista 3D compatible')
        self.canvas.pack(fill='both', expand=True)
        if not self._gpu:
            self.canvas.bind('<Configure>', lambda _e: self.schedule(), add='+')
        self.canvas.bind('<ButtonPress-1>', self.press, add='+')
        self.canvas.bind('<B1-Motion>', self.drag, add='+')
        self.canvas.bind('<ButtonRelease-1>', self.release, add='+')
        self.canvas.bind('<MouseWheel>', lambda e: self.change_zoom(1.12 if e.delta>0 else 1/1.12), add='+')
        self.canvas.bind('<Button-4>', lambda _e: self.change_zoom(1.12), add='+')
        self.canvas.bind('<Button-5>', lambda _e: self.change_zoom(1/1.12), add='+')
        self.canvas.bind('<Double-Button-1>', lambda _e: self.reset(), add='+')

    def _use_software(self):
        if self._closed:
            return
        self.canvas.destroy()
        self._gpu = False
        self.canvas = tk.Canvas(self.viewport, width=260, height=250, bg='#f6f9fd', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _e: self.schedule())
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.bind('<MouseWheel>', lambda e: self.change_zoom(1.12 if e.delta>0 else 1/1.12))
        self._engine.set('Vista 3D compatible')
        self.schedule()

    def press(self, event):
        self._last_mouse = (event.x, event.y)

    def drag(self, event):
        if self._last_mouse:
            x, y = self._last_mouse
            self.yaw += (event.x-x)*0.009
            self.tilt = max(-1.55, min(1.55, self.tilt+(event.y-y)*0.009))
            self._last_mouse = event.x, event.y
            self.schedule(fast=True)

    def release(self, _event):
        self._last_mouse = None
        self.schedule()

    def reset(self):
        self.yaw, self.tilt, self.zoom = 0.0, 0.75, 1.0
        self.schedule()

    def top(self):
        self.yaw, self.tilt = 0.0, math.pi/2
        self.schedule()

    def change_zoom(self, factor):
        self.zoom = max(0.4, min(4.0, self.zoom*factor))
        self.schedule(fast=self._last_mouse is not None)

    def schedule(self, fast=False):
        if self._closed:
            return
        if self._gpu:
            self.canvas.request_draw()
            return
        if self._pending is None:
            self._pending = self.after(16, lambda: self.draw(fast))

    def draw(self, fast=False):
        self._pending = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 10 or height < 10:
            return
        self._requested = (width, height, self.yaw, self.tilt, self.zoom, fast)
        if self._future is None:
            self._start_render()

    def _start_render(self):
        params, self._requested = self._requested, None
        self._future = self._executor.submit(self.model.render, *params)
        self._poll_id = self.after(40, self._poll_render)

    def _poll_render(self):
        self._poll_id = None
        if not self._future.done():
            self._poll_id = self.after(40, self._poll_render)
            return
        try:
            image = self._future.result()
            self._image = ImageTk.PhotoImage(image, master=self)
            self.canvas.delete('board')
            self.canvas.create_image(0, 0, image=self._image, anchor='nw', tags='board')
        except Exception:
            self.canvas.delete('board')
            self.canvas.create_text(25, 25, text='No se pudo dibujar la vista. Pulsa Restablecer vista.',
                                    anchor='nw', fill='#9a2929', tags='board')
        self._future = None
        if self._requested is not None:
            self._start_render()

    def _on_destroy(self, event):
        if event.widget is self:
            self._cleanup()

    def _cleanup(self):
        if self._closed:
            return
        self._closed = True
        for callback in (self._pending, self._poll_id):
            if callback is not None:
                self.after_cancel(callback)
        self._executor.shutdown(wait=False, cancel_futures=True)

    def close(self):
        self._cleanup()
        self.destroy()


class BoardViewer(tk.Toplevel):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.title('PlayRobot · Mi placa 3D')
        self.geometry('1050x760')
        self.minsize(700, 500)
        BoardSurface(self, model).pack(fill='both', expand=True)
        tk.Label(self, text='Modelo de referencia · Sin conexión en vivo a la ESP32',
                 bg='#fff1b8', fg='#594700', pady=7).pack(fill='x')
