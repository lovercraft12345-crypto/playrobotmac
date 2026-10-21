"""PlayRobot's shared visual shell and local project actions."""
import copy
import json
import math
from pathlib import Path
import tkinter as tk
from ui_theme import UI_FONT
from tkinter import filedialog, messagebox

ASSETS = Path(__file__).resolve().parent / 'assets'
INK, MUTED, BG, LINE = '#172449', '#66758e', '#f6f8fc', '#dfe6f0'
RED, YELLOW = '#ed163b', '#ffe16a'


def button(parent, text, command, bg='white', fg=INK, **kwargs):
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     activebackground=bg, activeforeground=fg, relief='flat', bd=0, highlightthickness=0,
                     padx=14, pady=10, font=(UI_FONT, 10, 'bold'), cursor='hand2', **kwargs)


class ModernMixin:
    def _modern_images(self):
        if getattr(self, '_modern_art', None):
            return self._modern_art
        self._modern_art = {}
        try:
            from PIL import Image, ImageTk
            specs = [('logo', 'playrobot-logo.png', (170, 110), True),
                     ('wordmark', 'playrobot-tipografia.png', (180, 45), True),
                     ('teacher', 'lesly-maestra-saludo-hires.png', (210, 235), False),
                     ('board', 'products/placa-preview.png', (250, 165), False),
                     ('tiny_board', 'products/placa-preview.png', (125, 92), False)]
            for key, filename, size, crop in specs:
                with Image.open(ASSETS / filename) as source:
                    image = source.convert('RGBA')
                    if crop:
                        from PIL import ImageChops
                        bounds = ImageChops.difference(image.convert('RGB'), Image.new('RGB', image.size, 'white')).getbbox()
                        if bounds:
                            image = image.crop(bounds)
                    image.thumbnail(size, Image.Resampling.LANCZOS)
                    self._modern_art[key] = ImageTk.PhotoImage(image, master=self)
        except (ImportError, OSError):
            pass
        return self._modern_art

    def _build_start_screen(self):
        from home_view import IllustratedHome
        self._modern_images()
        self._premium_buttons = []
        self.lesly_card_canvas = None
        self.lesly_card_item = None
        self.start_screen = self.home_view = IllustratedHome(self)
        self.start_screen.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.home_canvas = self.home_view.canvas

    def _scroll_to_levels(self):
        self._show_all_levels()

    def _show_all_levels(self):
        existing = getattr(self, '_levels_window', None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        self._modern_images()
        win = self._levels_window = tk.Toplevel(self)
        win.title('PlayRobot · Todos los niveles')
        win.geometry('1100x760')
        win.minsize(850, 550)
        win.configure(bg=BG)
        tk.Label(win, text='Elige tu próxima aventura', bg=BG, fg=INK,
                 font=(UI_FONT, 24, 'bold'), pady=18).pack(anchor='w', padx=20)
        outer=tk.Frame(win,bg=BG);outer.pack(fill='both',expand=True)
        canvas=tk.Canvas(outer,bg=BG,highlightthickness=0)
        scrollbar=tk.Scrollbar(outer,command=canvas.yview)
        scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        content=tk.Frame(canvas,bg=BG,padx=16,pady=12);content.columnconfigure(0,weight=1)
        item=canvas.create_window(0,0,window=content,anchor='nw')
        content.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        win.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120),'units'))
        levels=[
            ('led','01','Enciende un LED','Enciende y apaga una luz.','#fff0f2',''),
            ('motor','02','Controla motores','Dirección, giro y velocidad.','#eaf5ff',''),
            ('button_led','03','Programa un botón','Activa tu LED con una entrada.','#edf9f3',''),
            ('traffic','04','Crea un semáforo','Luces, tiempos y secuencias.','#fff6df',''),
            ('crossing','05','Cruce peatonal','Un botón y un semáforo.','#edf9f3',''),
            ('light','06','Luz automática','Enciende según la luz ambiente.','#f3efff',''),
            ('free','LIBRE','Tu propio proyecto','Todos los engranes sin un reto.','#f3efff',''),
            ('drive','07','Haz girar tu carrito','Controla cada rueda.','#eaf5ff',''),
            ('obstacle','08','Evita obstáculos','Mide antes de avanzar.','#edf9f3',''),
        ]
        for row in range(3):
            self._modern_cards(content,row,levels[row*3:row*3+3])
        button(content,'Volver al inicio',win.destroy,'#edf3fb').grid(row=4,column=0,sticky='e',pady=12)

    def _modern_cards(self, parent, row, items):
        grid = tk.Frame(parent, bg=BG)
        grid.grid(row=row, column=0, sticky='ew')
        for col, (mission, number, title, detail, color, icon) in enumerate(items):
            grid.columnconfigure(col, weight=1, uniform='cards')
            card = tk.Frame(grid, bg=color, padx=15, pady=15,
                            highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=col, sticky='nsew', padx=(0 if col==0 else 7, 0 if col==2 else 7))
            card.columnconfigure(0, weight=1)
            tk.Label(card, text=f'{number} · {title}', bg=color, fg=INK,
                     font=(UI_FONT, 13, 'bold'), wraplength=245, justify='left', anchor='w').grid(row=0, column=0, sticky='ew')
            tk.Label(card, text=detail, bg=color, fg=MUTED, font=(UI_FONT, 10),
                     wraplength=235, justify='left').grid(row=1, column=0, sticky='nw', pady=(10, 6))
            card.rowconfigure(1, weight=1)
            free = self._mission_is_free(mission)
            tk.Label(card, text='Gratis' if free else 'Premium', bg=YELLOW if free else '#e6ddff',
                     fg=INK, font=(UI_FONT, 9, 'bold'), padx=8, pady=4).grid(row=2, column=0, sticky='w', pady=6)
            if self._modern_art.get('tiny_board'):
                tk.Label(card, image=self._modern_art['tiny_board'], bg=color).grid(row=3, column=0, sticky='e', pady=4)
            action = button(card, 'Comenzar  →' if free else 'Premium · Ver acceso →',
                            lambda m=mission: self._select_mission(m), RED, 'white')
            action.grid(row=4, column=0, sticky='w', pady=(8, 0))
            if not free:
                self._premium_buttons.append(action)
        self._paint_account()

    def _build_workshop_header(self):
        self.workshop_header = header = tk.Frame(self, bg='white', padx=16, pady=8)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        nav = tk.Frame(header, bg='white')
        nav.grid(row=0, column=0, sticky='ew')
        if self._modern_images().get('wordmark'):
            tk.Label(nav, image=self._modern_art['wordmark'], bg='white').pack(side='left', padx=(0, 18), pady=8)
        titles = {'led': '01 · Enciende un LED', 'motor': '02 · Controla motores',
                  'button_led': '03 · Programa un botón', 'traffic': '04 · Crea un semáforo',
                  'crossing': '05 · Cruce peatonal', 'light': '06 · Luz automática',
                  'drive': '07 · Haz girar tu carrito', 'obstacle': '08 · Evita obstáculos', 'free': 'Modo libre'}
        tk.Label(nav, text=titles.get(self.mission, 'Taller de engranes'), bg='white', fg=INK,
                 font=(UI_FONT, 17, 'bold')).pack(side='left')
        for text, action in [('Mi cuenta', self._open_account), ('Productos', self._open_products), ('← Niveles', self._go_home)]:
            button(nav, text, action).pack(side='right', padx=4)
        self.workshop_toolbar = tk.Frame(header, bg='white')
        self.workshop_toolbar.grid(row=1, column=0, sticky='ew', pady=(8, 0))

    def _arrange_workshop_controls(self):
        controls = self.workshop_toolbar
        for col in range(10):
            controls.columnconfigure(col, weight=0)
        controls.columnconfigure(9, weight=1)
        for text, action, col, bg, fg in [
            ('Guardar', self._save_project, 0, YELLOW, INK),
            ('Abrir', self._open_project, 1, '#edf3fb', INK),
            ('Deshacer', self._undo_program, 2, '#edf3fb', INK),
            ('■ Detener', self._stop_program, 4, '#fff0f2', RED),
        ]:
            button(controls, text, action, bg, fg).grid(row=0, column=col, padx=(0, 7))
        self.run_button.grid_configure(row=0, column=3, padx=(0, 7))
        self.run_button.configure(text='▶ Correr', bg='#25ad5b', activebackground='#1d924b')
        self.toggle_code_button.grid_remove()
        self.toolbar_code_button = button(controls, 'Ver código', self._toggle_code_panel, '#edf3fb')
        self.toolbar_code_button.grid(row=0, column=5, padx=(0, 7))
        self.toolbar_board_button = button(controls, 'Ocultar placa', self._toggle_board_panel, '#edf3fb')
        self.toolbar_board_button.grid(row=0, column=6, padx=(0, 7))
        self.step_mode_button.grid_configure(row=1, column=0, columnspan=2, padx=0, pady=(8, 0), sticky='w')
        self.next_step_button.grid_configure(row=1, column=2, columnspan=2, pady=(8, 0), sticky='w')
        self.toggle_esp32_controls_button.grid_configure(row=1, column=4, columnspan=2, pady=(8, 0), sticky='w')
        self.status.grid_configure(row=1, column=6, columnspan=4, sticky='e', pady=(8, 0))
        self.status.configure(wraplength=340, justify='right', bg='white')
        self.step_message_label.grid_configure(row=2, column=0, columnspan=10)
        self.esp32_controls_frame.grid_configure(row=3, column=0, columnspan=10)
        if not self.step_mode_enabled:
            self.step_message_label.grid_remove()
        if not self.esp32_controls_visible:
            self.esp32_controls_frame.grid_remove()
        self._compact_simulator()
        self._build_board_panel()

    def _compact_simulator(self):
        machine = self.simulation_card
        def wrap(parent):
            for child in parent.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(wraplength=250, justify='left')
                elif isinstance(child, tk.Canvas):
                    child.configure(width=255)
                if isinstance(child, tk.Frame):
                    wrap(child)
        wrap(machine)
        for name in ('traffic_canvas', 'car_canvas'):
            scene = getattr(self, name, None)
            if scene is not None and scene.winfo_exists() and scene.master is machine:
                scroll = tk.Scrollbar(machine, orient='horizontal', command=scene.xview)
                scroll.grid(row=8, column=0, sticky='ew', padx=10, pady=(0, 6))
                scene.configure(xscrollcommand=scroll.set, scrollregion=(0, 0, 650, scene.winfo_reqheight()))
        for child in machine.winfo_children():
            info = child.grid_info()
            if info and int(info.get('column', 0)) > 0:
                child.grid_configure(row=5 if isinstance(child, tk.Scale) else 3,
                                     column=0, columnspan=1, sticky='ew')
            if isinstance(child, tk.Frame) and info and int(info.get('row', 0)) == 0:
                for row, widget in enumerate(child.winfo_children()):
                    if widget.winfo_manager() == 'grid':
                        widget.grid_configure(row=row, column=0, sticky='w', padx=0)
            if isinstance(child, tk.Frame) and child.winfo_children() and child.winfo_children()[0].winfo_manager() == 'pack':
                for widget in child.winfo_children():
                    widget.pack_configure(side='top', anchor='w', padx=0)

    def _stop_program(self):
        if self.running:
            self._toggle_run()

    def _build_board_panel(self):
        box = tk.Frame(self.inspector, bg='white', highlightbackground=LINE, highlightthickness=1)
        box.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        box.rowconfigure(1, weight=1)
        box.columnconfigure(0, weight=1)
        heading = tk.Frame(box, bg='white')
        heading.grid(row=0, column=0, sticky='ew', padx=12, pady=12)
        tk.Label(heading, text='Mi placa 3D', bg='white', fg=INK, font=(UI_FONT, 14, 'bold')).pack(side='left')
        tk.Label(heading, text='Referencia', bg='#eaf5ff', fg='#23658c',
                 font=(UI_FONT, 8, 'bold'), padx=8, pady=5).pack(side='right')
        try:
            from board_viewer import BoardModel, BoardSurface
            if getattr(self, '_board_model', None) is None:
                self._board_model = BoardModel(ASSETS / 'models/playrobot.3ds')
            surface = BoardSurface(box, self._board_model, compact=True)
            surface.grid(row=1, column=0, sticky='nsew')
        except (ImportError, OSError, ValueError):
            button(box, 'Abrir visor de placa', self._open_board_viewer, '#edf3fb').grid(row=1, column=0, pady=20)
        tk.Label(box, text='Arrastra para girar · rueda para acercar', bg='white', fg=MUTED,
                 font=(UI_FONT, 8), pady=7).grid(row=2, column=0, sticky='ew')
        self.board_visible = True

    def _toggle_board_panel(self):
        self.board_visible = not self.board_visible
        if self.board_visible:
            self.code_visible = False
        self._layout_side_panels()

    def _layout_side_panels(self):
        if self.board_visible:
            self.inspector.grid()
            self.main_container.columnconfigure(2, weight=0, minsize=285)
        else:
            self.inspector.grid_remove()
            self.main_container.columnconfigure(2, weight=0, minsize=0)
        self.toolbar_board_button.configure(text='Ocultar placa' if self.board_visible else 'Ver placa')
        if self.code_visible:
            self.code_panel.grid()
            self.main_container.columnconfigure(3, weight=1, minsize=330)
        else:
            self.code_panel.grid_remove()
            self.main_container.columnconfigure(3, weight=0, minsize=0)
        self.toolbar_code_button.configure(text='Ocultar código' if self.code_visible else 'Ver código')

    def _snapshot_program(self):
        return copy.deepcopy({name: getattr(self, name) for name in
            ('steps', 'parameters', 'loose_steps', 'loose_parameters', 'loose_positions')})

    def _remember_program(self):
        if self.running or getattr(self, '_restoring_program', False):
            return
        snapshot = self._snapshot_program()
        history = getattr(self, '_program_history', [])
        if not history or history[-1] != snapshot:
            history.append(snapshot)
            self._program_history = history[-50:]

    def _undo_program(self):
        if self.running:
            return
        self._remember_program()
        if len(getattr(self, '_program_history', [])) < 2:
            self.status.configure(text='Todavía no hay cambios para deshacer.')
            return
        self._program_history.pop()
        self._restore_program(self._program_history[-1])
        self.status.configure(text='Último cambio deshecho.')

    def _restore_program(self, data):
        self._restoring_program = True
        try:
            # Editors from the previous recipe must not overwrite restored GPIOs.
            self._led_editor_signature = None
            for name, value in data.items():
                setattr(self, name, copy.deepcopy(value))
            self._sync_connected_settings()
            self._render_steps()
            self._refresh_code()
        finally:
            self._restoring_program = False

    def _save_project(self):
        if self.running:
            self.status.configure(text='Detén la simulación antes de guardar.')
            return
        if self.active_challenge:
            messagebox.showinfo('Guardar proyecto', 'Guarda tus ideas en un tutorial o en modo libre.', parent=self)
            return
        if self.mission in ('led', 'button_led', 'traffic', 'crossing', 'light'):
            self._save_led_pins()
        path = filedialog.asksaveasfilename(parent=self, title='Guardar proyecto PlayRobot',
                    defaultextension='.playrobot', filetypes=[('Proyecto PlayRobot', '*.playrobot')])
        if not path:
            return
        payload = {'format': 'playrobot-project', 'version': 1, 'mission': self.mission,
                   'challenge': self.active_challenge, 'program': self._snapshot_program()}
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            self.status.configure(text='Proyecto guardado en tu computadora.')
        except OSError as exc:
            messagebox.showerror('Guardar proyecto', str(exc), parent=self)

    def _open_project(self):
        if getattr(self, 'running', False):
            messagebox.showinfo('Abrir proyecto', 'Detén la simulación antes de abrir otro proyecto.', parent=self)
            return
        path = filedialog.askopenfilename(parent=self, title='Abrir proyecto PlayRobot',
                    filetypes=[('Proyecto PlayRobot', '*.playrobot')])
        if not path:
            return
        try:
            if Path(path).stat().st_size > 1_000_000:
                raise ValueError('El archivo es demasiado grande.')
            data = validate_project(json.loads(Path(path).read_text(encoding='utf-8')))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror('Abrir proyecto', f'No se pudo abrir: {exc}', parent=self)
            return
        def load():
            if not self.on_home_screen:
                self._go_home()
            self._select_mission(data['mission'], challenge=data.get('challenge'), _access_checked=True)
            self._restore_program(data['program'])
            self._program_history = [self._snapshot_program()]
            self.status.configure(text='Proyecto abierto. ¡Continúa creando!')
        if self._mission_is_free(data['mission'], data.get('challenge')):
            load()
        else:
            self._require_mission_access(data['mission'], data.get('challenge'), load)


def validate_project(data):
    if not isinstance(data, dict) or data.get('format') != 'playrobot-project' or data.get('version') != 1:
        raise ValueError('No es un proyecto compatible con PlayRobot.')
    if data.get('mission') not in {'led', 'motor', 'button_led', 'traffic', 'crossing', 'light', 'free', 'drive', 'obstacle', 'parking', 'final'}:
        raise ValueError('Nivel desconocido.')
    if data.get('challenge') is not None and not isinstance(data['challenge'], dict):
        raise ValueError('Reto inválido.')
    # Current catalog saves tutorials/levels, not imported arbitrary challenge definitions.
    if data.get('challenge'):
        raise ValueError('Este archivo de reto requiere la definición original del curso.')
    program = data['program']
    if not isinstance(program, dict):
        raise ValueError('El contenido del programa es inválido.')
    allowed = {'start', 'led', 'off', 'wait', 'repeat', 'motor_on', 'motor_off', 'direction', 'speed',
        'left_forward', 'left_reverse', 'left_stop', 'right_forward', 'right_reverse', 'right_stop',
        'button_wait', 'light_intensity', 'red_on', 'red_off', 'yellow_on', 'yellow_off', 'green_on',
        'green_off', 'pedestrian_on', 'pedestrian_off', 'light_threshold', 'light_auto', 'threshold',
        'avoid', 'gate_auto', 'smart_drive'}
    for steps, params in [('steps', 'parameters'), ('loose_steps', 'loose_parameters')]:
        if not isinstance(program.get(steps), list) or not isinstance(program.get(params), list):
            raise ValueError('Faltan los engranes o sus parámetros.')
        if len(program[steps]) != len(program[params]) or len(program[steps]) > 300:
            raise ValueError('Cantidad de engranes inválida.')
        if any(not isinstance(x, str) or x not in allowed for x in program[steps]):
            raise ValueError('Engrane desconocido.')
        if any(type(x) is not int or not 0 <= x <= 10000 for x in program[params]):
            raise ValueError('Parámetro inválido.')
    positions = program.get('loose_positions')
    if not isinstance(positions, list) or len(positions) != len(program['loose_steps']):
        raise ValueError('Faltan posiciones de los engranes sueltos.')
    for pair in positions:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(type(x) not in (int, float) or abs(x)>100000 or not math.isfinite(x) for x in pair):
            raise ValueError('Posición inválida.')
    data['program'] = {key: program[key] for key in ('steps', 'parameters', 'loose_steps', 'loose_parameters', 'loose_positions')}
    return data
