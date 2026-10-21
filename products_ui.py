"""Product catalog and entry points to the actual exported PlayRobot board."""
import tkinter as tk
from ui_theme import UI_FONT
from tkinter import ttk, messagebox
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets'


class ProductsMixin:
    def _open_board_viewer(self):
        window = getattr(self, '_board_viewer_window', None)
        if window is not None and window.winfo_exists():
            window.deiconify()
            window.lift()
            return
        try:
            from board_viewer import BoardModel, BoardViewer
            model = getattr(self, '_board_model', None)
            if model is None:
                model = self._board_model = BoardModel(ASSETS / 'models' / 'playrobot.3ds')
            self._board_viewer_window = BoardViewer(self, model)
        except ImportError:
            messagebox.showerror('Visor 3D',
                'Faltan las dependencias del visor. Instala requirements-desktop.txt y vuelve a abrir el programa.', parent=self)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Visor 3D', f'No se pudo abrir la placa: {exc}', parent=self)

    def _open_products(self):
        existing = getattr(self, '_products_window', None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        win = self._products_window = tk.Toplevel(self)
        win.title('PlayRobot · Productos')
        win.geometry('920x740')
        win.minsize(650, 500)
        win.configure(bg='#eef3f8')
        header = tk.Frame(win, bg='white', padx=24, pady=18)
        header.pack(fill='x')
        tk.Label(header, text='Productos PlayRobot', bg='white', fg='#172449',
                 font=(UI_FONT, 21, 'bold')).pack(anchor='w')
        tk.Label(header, text='Conoce la electrónica con la que puedes crear.', bg='white',
                 fg='#66758e', font=(UI_FONT, 11)).pack(anchor='w', pady=(5, 0))
        body = tk.Frame(win, bg='#eef3f8')
        body.pack(fill='both', expand=True)
        canvas = tk.Canvas(body, bg='#eef3f8', highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        content = tk.Frame(canvas, bg='#eef3f8', padx=22, pady=18)
        item = canvas.create_window(0, 0, window=content, anchor='nw')
        content.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(item, width=e.width))
        win.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-int(e.delta/120), 'units'))
        card = tk.Frame(content, bg='white', padx=22, pady=18,
                        highlightbackground='#d7e0eb', highlightthickness=1)
        card.pack(fill='x')
        tk.Label(card, text='PLACA EDUCATIVA PLAYROBOT', bg='white', fg='#123659',
                 font=(UI_FONT, 17, 'bold'), wraplength=540, justify='left').pack(anchor='w')
        try:
            from PIL import Image, ImageTk
            image = Image.open(ASSETS / 'products' / 'placa-preview.png')
            image.thumbnail((520, 280))
            win._product_photo = ImageTk.PhotoImage(image, master=win)
            tk.Label(card, image=win._product_photo, bg='#eaf0f6').pack(pady=12)
        except (ImportError, OSError):
            pass
        tk.Label(card, text='Tu taller de electrónica en una placa con forma de engrane.', bg='white',
                 fg='#263c55', font=(UI_FONT, 12), wraplength=560, justify='left').pack(anchor='w')
        tk.Label(card, text='ESP32 extraíble · LED rojo, amarillo y verde · Sensor ultrasónico\n'
                 'L293D y conexiones para dos motores · Buzzer · Pines de expansión',
                 bg='white', fg='#52677d', font=(UI_FONT, 11), wraplength=560,
                 justify='left').pack(anchor='w', pady=12)
        tk.Button(card, text='Explorar placa en 3D →', command=self._open_board_viewer,
                  bg='#ed163b', fg='white', relief='flat', padx=18, pady=12,
                  font=(UI_FONT, 12, 'bold'), cursor='hand2').pack(anchor='w')
        tk.Label(card, text='Precio y disponibilidad: por confirmar.', bg='white', fg='#63758a',
                 font=(UI_FONT, 10)).pack(anchor='w', pady=(12, 0))
        ttk.Button(content, text='Volver al taller', command=win.destroy).pack(anchor='e', pady=15)
