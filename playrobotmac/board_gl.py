"""Event-driven OpenGL surface. No background animation or per-frame mesh rebuild."""
import math
import sys
import numpy as np
from OpenGL import GL
from pyopengltk import OpenGLFrame


class BoardGLCanvas(OpenGLFrame):
    def __init__(self, parent, model, view, on_failure, **kwargs):
        self.model, self.view, self.on_failure = model, view, on_failure
        self._failed = False
        self._ready = False
        self._draw_id = None
        super().__init__(parent, **kwargs)
        self.bind('<Destroy>', self._cleanup, add='+')

    def _fail(self):
        if not self._failed:
            self._failed = True
            self.after_idle(self.on_failure)

    def tkMap(self, event):
        try:
            super().tkMap(event)
            if not GL.glGetString(GL.GL_VERSION):
                raise RuntimeError('No OpenGL context')
            self.request_draw()
        except Exception:
            self._fail()

    def tkResize(self, event):
        self.width, self.height = event.width, event.height
        if self.context_created:
            self.request_draw()

    def initgl(self):
        if sys.platform == 'win32':
            from OpenGL.WGL import wglGetCurrentContext, wglGetCurrentDC
            self._owned_context = wglGetCurrentContext()
            self._owned_dc = wglGetCurrentDC()
        GL.glClearColor(0.963, 0.976, 0.992, 1)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        if not self._ready:
            triangles = self.model.vertices[self.model.faces]
            normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
            normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
            self._vertices = np.ascontiguousarray(triangles.reshape(-1, 3), dtype=np.float32)
            self._normals = np.ascontiguousarray(np.repeat(normals, 3, axis=0), dtype=np.float32)
            self._colors = np.ascontiguousarray(np.repeat(np.clip((self.model.colors+12)/255, 0, 1), 3, axis=0), dtype=np.float32)
            self._ready = True
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
        GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, [0.48, 0.48, 0.48, 1])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.65, 0.65, 0.65, 1])
        GL.glEnable(GL.GL_NORMALIZE)

    def redraw(self):
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        GL.glViewport(0, 0, width, height)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        scale = min(width, height)*0.81*self.view.zoom
        GL.glOrtho(-width/(2*scale), width/(2*scale), -height/(2*scale), height/(2*scale), -5, 5)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [-0.3, 0.5, 0.8, 0])
        cy, sy = math.cos(self.view.yaw), math.sin(self.view.yaw)
        ct, st = math.cos(self.view.tilt), math.sin(self.view.tilt)
        rotation = np.array([[cy, -sy, 0, 0], [-sy*st, -cy*st, ct, 0],
                             [sy*ct, cy*ct, st, 0], [0, 0, 0, 1]], dtype=np.float32)
        GL.glLoadMatrixf(rotation.T.copy())
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, self._vertices)
        GL.glColorPointer(3, GL.GL_FLOAT, 0, self._colors)
        GL.glNormalPointer(GL.GL_FLOAT, 0, self._normals)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(self._vertices))
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

    def _display(self):
        if self._failed or not self.context_created or not self.winfo_ismapped():
            return
        try:
            self.tkMakeCurrent()
            self.redraw()
            self.tkSwapBuffers()
        except Exception:
            self._fail()

    def request_draw(self):
        if self._draw_id is None and not self._failed:
            self._draw_id = self.after(16, self._draw)

    def _draw(self):
        self._draw_id = None
        self._display()

    def _cleanup(self, event):
        if event.widget is not self:
            return
        if self._draw_id is not None:
            self.after_cancel(self._draw_id)
            self._draw_id = None
        if sys.platform == 'win32' and getattr(self, '_owned_context', None):
            from OpenGL.WGL import wglMakeCurrent, wglDeleteContext, wglGetCurrentContext
            try:
                if wglGetCurrentContext() == self._owned_context:
                    wglMakeCurrent(None, None)
                wglDeleteContext(self._owned_context)
                from ctypes import WinDLL, c_void_p, c_int
                release = WinDLL('user32').ReleaseDC
                release.argtypes = [c_void_p, c_void_p]
                release.restype = c_int
                release(self._wid, self._owned_dc)
            except Exception:
                pass
            self._owned_context = None
