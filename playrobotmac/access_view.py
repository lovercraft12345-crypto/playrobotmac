"""Warm illustrated access screen with real Entry controls and existing auth API."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from home_view import IllustratedHome, gear, INK, RED, MUTED
from ui_theme import UI_FONT

ASSETS = Path(__file__).resolve().parent / 'assets'


class PlaceholderEntry(tk.Entry):
    def __init__(self, parent, variable, placeholder='', **kwargs):
        super().__init__(parent, textvariable=variable, bg='white', fg=INK,
                         relief='flat', bd=0, highlightthickness=0,
                         insertbackground=INK, selectbackground='#dceaff', **kwargs)
        self.variable = variable
        self.placeholder = tk.Label(self, text=placeholder, bg='white', fg='#919bb2',
                                    cursor='xterm', anchor='w', padx=0)
        self.placeholder.bind('<Button-1>', lambda _e: self.focus_set())
        self.bind('<FocusIn>', lambda _e: self.placeholder.place_forget())
        self.bind('<FocusOut>', lambda _e: self.update_placeholder())
        self._trace = variable.trace_add('write', lambda *_a: self.update_placeholder())
        self.bind('<Destroy>', self._destroyed)

    def update_placeholder(self):
        if not self.winfo_exists():
            return
        if not self.variable.get() and self.focus_get() is not self:
            self.placeholder.place(x=0, rely=.5, relwidth=1, anchor='w')
        else:
            self.placeholder.place_forget()

    def _destroyed(self, event):
        if event.widget is self:
            self.variable.trace_remove('write', self._trace)


class AccessView(IllustratedHome):
    def __init__(self, parent, app):
        tk.Frame.__init__(self, parent, bg='#fffdf9')
        self.app = app
        self.mode = 'dashboard' if app.account_client.token else 'login'
        self._was_logged = bool(app.account_client.token)
        self.message = ''
        self.busy = app._account_busy
        self.actions, self._photos = [], []
        self._draw_id, self._focus_index = None, -1
        self._focus_id = None
        self._scale, self._offset = 1., (0, 0)
        self.heading_font = UI_FONT
        self.canvas = tk.Canvas(self, bg='#fffdf9', highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='both', expand=True)
        self._sources = self._load_art()
        self._server_window = None
        app._account_email_var = tk.StringVar(parent, value=app.account_info.get('email') or getattr(app, '_account_remembered_email', ''))
        app._account_password_var = tk.StringVar(parent)
        app._account_confirm_var = tk.StringVar(parent)
        app._account_show_password = tk.BooleanVar(parent, value=False)
        app._account_remember_var = tk.BooleanVar(parent, value=bool(getattr(app, '_account_remembered_email', '')))
        app._account_server_var = tk.StringVar(parent, value=app.account_client.base_url)
        self.email = PlaceholderEntry(self.canvas, app._account_email_var,
                                      'Correo de tu mamá, papá o tutor')
        self.password = PlaceholderEntry(self.canvas, app._account_password_var,
                                         'Tu contraseña de PlayRobot', show='•')
        self.confirm = PlaceholderEntry(self.canvas, app._account_confirm_var,
                                        'Escribe otra vez tu contraseña', show='•')
        app._account_password_entries = [self.password, self.confirm]
        self.progress = ttk.Progressbar(self.canvas, mode='indeterminate')
        self.canvas.bind('<Configure>', self._resize)
        self.canvas.bind('<Motion>', self._hover)
        self.canvas.bind('<Button-1>', self._click)
        self.canvas.bind('<Tab>', lambda e: self._focus(1))
        self.canvas.bind('<Shift-Tab>', lambda e: self._focus(-1))
        self.canvas.bind('<Return>', self._activate)
        self.canvas.bind('<space>', self._activate)
        self.bind('<Destroy>', self._destroyed, add='+')
        self.email.bind('<Tab>', lambda _e: self._field_tab(self.password))
        self.password.bind('<Tab>', lambda _e: self._field_tab(self.confirm if self.mode=='register' else None))
        self.confirm.bind('<Tab>', lambda _e: self._field_tab(None))
        self.after_idle(self._resize)

    def _load_art(self):
        art = {}
        with Image.open(ASSETS/'lesly-maestra-saludo-hires.png') as source:
            art['teacher'] = source.convert('RGBA')
        logo = Image.new('RGBA', (510, 110))
        with Image.open(ASSETS/'playrobot-emblema.png') as source:
            image=source.convert('RGBA');image.thumbnail((95,95),Image.Resampling.LANCZOS)
            logo.alpha_composite(image,(0,7))
        with Image.open(ASSETS/'playrobot-tipografia.png') as source:
            image=source.convert('RGBA');image=image.crop(image.getbbox());image.thumbnail((400,98),Image.Resampling.LANCZOS)
            logo.alpha_composite(image,(108,6))
        art['brand']=logo
        return art

    def _field_tab(self, target):
        if target is not None:
            target.focus_set()
        else:
            self.canvas.focus_set()
            self._focus_index = next((i for i,a in enumerate(self.actions) if a[0] in ('Entrar a mi cuenta  →','Crear mi cuenta  →')),0)
            self._draw_focus()
        return 'break'

    def _click(self, event):
        index=self._at(event)
        if index is not None:
            self._focus_index=index
            self.actions[index][2]()

    def refresh(self):
        self.busy=self.app._account_busy
        logged=bool(self.app.account_client.token)
        if logged:
            self.mode='dashboard'
        elif self._was_logged:
            self.mode='login'
        self._was_logged=logged
        self._resize()

    def set_message(self, text, busy=False):
        self.message, self.busy = text[:180]+('…' if len(text)>180 else ''), busy
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        self._resize()

    def focus_email(self):
        if self._focus_id is not None:
            self.after_cancel(self._focus_id)
        self._focus_id = self.after(80, self._focus_email_now)

    def _focus_email_now(self):
        self._focus_id = None
        if self.mode != 'dashboard':
            self.email.focus_set()

    def _destroyed(self, event):
        if event.widget is self and self._focus_id is not None:
            self.after_cancel(self._focus_id)
            self._focus_id=None
        super()._destroyed(event)

    def choose_mode(self, mode):
        if self.busy:
            return
        self.mode=mode
        self.message=''
        self._focus_index=-1
        self._resize()

    def submit(self):
        if not self.busy and self.mode in ('login','register'):
            self.app._account_auth(self.mode)

    def enter(self):
        if not self.busy:
            self.app._enter_workshop()

    def toggle_password(self):
        self.app._account_show_password.set(not self.app._account_show_password.get())
        self.app._toggle_account_password()
        self._resize()

    def remember(self):
        self.app._account_remember_var.set(not self.app._account_remember_var.get())
        self._resize()

    def _entry(self, widget, bounds):
        x,y,w,h=bounds;s=self._scale
        widget.configure(font=(UI_FONT,-max(12,round(21*s))), state='disabled' if self.busy else 'normal')
        widget.placeholder.configure(font=(UI_FONT,-max(11,round(20*s))))
        self.canvas.create_window(*self._xy(x,y),anchor='nw',window=widget,
                                   width=round(w*s),height=round(h*s))
        widget.update_placeholder()

    def _eye(self,y):
        cx=1492;s=self._scale
        self.canvas.create_oval(*self._xy(cx-13,y-8),*self._xy(cx+13,y+8),outline=MUTED,width=2*s)
        self.canvas.create_oval(*self._xy(cx-4,y-4),*self._xy(cx+4,y+4),fill=MUTED,outline='')
        if self.app._account_show_password.get():
            self.canvas.create_line(*self._xy(cx-14,y+11),*self._xy(cx+14,y-11),fill=RED,width=2*s)
        self._action('Mostrar u ocultar contraseña',(1465,y-22,1522,y+22),self.toggle_password)

    def _checkbox(self,y):
        x=930;s=self._scale
        self.canvas.create_rectangle(*self._xy(x,y-13),*self._xy(x+26,y+13),
                                     fill=RED if self.app._account_remember_var.get() else 'white',
                                     outline=RED if self.app._account_remember_var.get() else MUTED,width=2*s)
        if self.app._account_remember_var.get():
            self.canvas.create_line(*self._xy(x+5,y),*self._xy(x+11,y+6),*self._xy(x+21,y-7),fill='white',width=3*s)
        self._text(x+40,y,'Recordar mi correo',20,anchor='w')
        self._action('Recordar mi correo',(925,y-20,1260,y+20),self.remember)

    def _draw(self):
        self._draw_id=None
        w,h=self.canvas.winfo_width(),self.canvas.winfo_height()
        if w<50 or h<50:return
        focused=self.focus_get()
        self._scale=min(w/1600,h/1000)
        self._offset=((w-1600*self._scale)/2,(h-1000*self._scale)/2)
        self.canvas.delete('all');self.actions.clear();self._photos.clear()
        self._background(w,h)
        self._image('brand',(50,22,335,75))
        self._text(1325,36,'Taller de engranes',22,MUTED)
        self._text(52,125,'¡Tu próxima aventura',70,heading=True,width=790)
        self._text(52,209,'empieza aquí!',89,RED,heading=True)
        self._text(59,296,'Aprende a programar, engrane por engrane.',27,width=785)
        self._image('teacher',(5,337,635,663),crop=True)
        self._text(671,444,'¡Hola!\nSoy Lesly.\n¿Listo para\ncrear?',29,heading=True,width=177,
                   font_path=ASSETS/'fonts/Kalam-Bold.ttf')
        self._text(691,753,'6 tutoriales\ngratis',26,heading=True,width=160)
        self._text(691,868,'Crea con\nengranes',26,heading=True,width=160)
        if self.mode=='dashboard':
            self._dashboard()
        else:
            self._form()
        self._text(920,976,'Configuración de conexión',18,MUTED,anchor='w')
        self._action('Configuración de conexión',(900,956,1225,997),self.open_server)
        self._text(1270,976,'Una idea. Muchos engranes por descubrir.',15,MUTED,anchor='w')
        self._draw_focus()
        visible=[self.email,self.password]+([self.confirm] if self.mode=='register' else [])
        if self.mode!='dashboard' and focused in visible:
            focused.focus_set()

    def _form(self):
        signup=self.mode=='register'
        self._text(1230,149,'Bienvenido a PlayRobot',48,heading=True,anchor='center')
        self._text(1230,216,'Crea tu cuenta y comienza gratis.' if signup else 'Entra y continúa creando.',23,MUTED,anchor='center')
        self._text(1080,292,'Iniciar sesión',25,RED if not signup else MUTED,heading=True,anchor='center')
        self._text(1385,292,'Crear cuenta',25,RED if signup else MUTED,heading=True,anchor='center')
        self._action('Iniciar sesión',(932,263,1230,323),lambda:self.choose_mode('login'))
        self._action('Crear cuenta',(1230,263,1532,323),lambda:self.choose_mode('register'))
        self._text(930,351,'Correo electrónico' if signup else 'Correo o usuario',24,heading=True)
        self._entry(self.email,(992,399,516,38))
        self._text(930,480,'Contraseña · mínimo 12 caracteres' if signup else 'Contraseña',24,heading=True)
        self._entry(self.password,(992,528,475,38));self._eye(546)
        if signup:
            self._text(930,594,'Confirma tu contraseña',23,heading=True)
            self._entry(self.confirm,(992,640,475,36));self._eye(658)
            self._checkbox(711)
            self._pill(930,750,602,66,'Crear mi cuenta  →',self.submit,size=28)
            self._message(828)
            self._pill(930,857,602,65,'Entrar como invitado  →',self.enter,foreground=INK,size=27)
            self._text(1231,936,'Tu cuenta comienza gratis. Premium es opcional.',16,MUTED,anchor='center')
        else:
            self._checkbox(615)
            self._text(1454,615,'Ayuda para entrar',19,MUTED,anchor='center')
            self._action('Ayuda para entrar',(1360,591,1540,638),self.app._account_access_help)
            self._pill(930,655,602,70,'Entrar a mi cuenta  →',self.submit,size=29)
            self._message(763)
            self._pill(930,815,602,70,'Entrar como invitado  →',self.enter,foreground=INK,size=29)
            self._text(1231,919,'Prueba los primeros 6 tutoriales gratis.',20,MUTED,anchor='center')

    def _message(self,y):
        if self.message:
            self._text(940,y-12,self.message,16,MUTED if self.busy else '#925139',width=580)
        elif self.mode=='login':
            self._text(1230,y+5,'o explora primero',20,MUTED,anchor='center')
        if self.busy:
            self.canvas.create_window(*self._xy(936,y-26),window=self.progress,anchor='nw',width=round(590*self._scale),height=max(3,round(5*self._scale)))

    def _dashboard(self):
        info=self.app.account_info;premium=info.get('premium') is True
        self._text(1230,157,'Tu cuenta PlayRobot',49,heading=True,anchor='center')
        self._text(1230,230,info.get('email','Consultando tu cuenta…'),21,MUTED,anchor='center',width=610)
        self._text(970,335,'Premium activo' if premium else 'Tu plan gratuito',39,heading=True)
        self._text(970,401,'Tutoriales 1–6 disponibles para aprender.\nPremium: niveles 7–8 y modo libre.',23,MUTED,width=550)
        price=info.get('premium_monthly_price_mxn')
        self._text(970,491,f'Suscripción mensual: ${price} MXN' if price else 'Actualiza tu cuenta para consultar el precio.',21,MUTED,width=550)
        if not premium:
            self._pill(930,561,602,63,'Activar Premium · Ver pago',self.app._account_checkout,size=26)
        self._pill(930,642,602,59,'Ya pagué · Actualizar Premium',lambda:self.app._refresh_account(sync=True),foreground=INK,size=23)
        self._text(1230,733,'Cerrar mi sesión',20,RED,anchor='center')
        self._action('Cerrar mi sesión',(1115,710,1345,750),self.app._account_logout)
        self._message(785)
        self._pill(930,841,602,70,'Entrar al taller  →',self.enter,foreground=INK,size=29)

    def _background(self,width,height):
        layer=Image.new('RGBA',(1600,1000),'#fffdf9')
        shadow=Image.new('RGBA',layer.size)
        ImageDraw.Draw(shadow).rounded_rectangle((875,98,1580,955),38,fill=(50,35,20,24))
        layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
        d=ImageDraw.Draw(layer)
        d.rounded_rectangle((875,88,1580,949),38,fill='white')
        d.rounded_rectangle((20,373,835,974),120,fill='#fff0b4')
        deco=Image.new('RGBA',layer.size);dd=ImageDraw.Draw(deco)
        for x,y,r in [(81,902,89),(92,602,80),(110,439,29),(800,355,63),(761,652,32)]:
            gear(dd,x,y,r,(249,198,62,95))
        layer.alpha_composite(deco);d=ImageDraw.Draw(layer)
        d.rounded_rectangle((638,424,859,645),62,fill='white')
        d.polygon([(669,620),(650,654),(709,630)],fill='white')
        for y in (726,839):
            d.rounded_rectangle((607,y,848,y+99),48,fill='#ffe9ec' if y==726 else '#fff7d2')
            d.ellipse((625,y+18,687,y+80),fill=RED)
        # Bulb and cog illustrations are native shapes, consistent with the app.
        d.ellipse((646,754,667,779),outline='white',width=4)
        d.line((650,783,663,783),fill='white',width=4)
        gear(d,655,888,22,'white')
        if self.mode in ('login','register'):
            d.rounded_rectangle((930,262,1532,324),24,fill='#f7f7fb',outline='#e1e5ef',width=2)
            selected=(1233,266,1527,320) if self.mode=='register' else (934,266,1230,320)
            d.rounded_rectangle(selected,22,fill='#ffe9ee',outline='#ffd4de',width=2)
            for y in ([389,518,630] if self.mode=='register' else [389,518]):
                d.rounded_rectangle((930,y,1532,y+66),20,fill='white',outline='#d7ddeb',width=2)
                if y==389:
                    d.rectangle((951,y+23,976,y+43),outline=MUTED,width=3)
                    d.line((952,y+24,963,y+33,975,y+24),fill=MUTED,width=2)
                else:
                    d.rounded_rectangle((953,y+26,974,y+45),4,outline=MUTED,width=3)
                    d.arc((958,y+15,969,y+32),180,360,fill=MUTED,width=3)
            red_y=750 if self.mode=='register' else 655
            guest_y=857 if self.mode=='register' else 815
            d.rounded_rectangle((930,red_y,1532,red_y+66),33,fill='#ef5670' if self.busy else RED)
            d.rounded_rectangle((930,guest_y,1532,guest_y+70),35,fill='#ffe584')
        else:
            d.rounded_rectangle((940,301,1522,527),22,fill='#f2f7ff')
            if not self.app.account_info.get('premium'):
                d.rounded_rectangle((930,561,1532,624),31,fill=RED)
            d.rounded_rectangle((930,642,1532,701),29,fill='#edf3fd')
            d.rounded_rectangle((930,841,1532,911),35,fill='#ffe584')
        for x,y in [(652,243),(820,709),(822,846),(650,367)]:
            d.line((x,y,x+12,y-21),fill='#ffc300',width=7)
        image=layer.resize((round(1600*self._scale),round(1000*self._scale)),Image.Resampling.LANCZOS)
        photo=ImageTk.PhotoImage(image,master=self);self._photos.append(photo)
        self.canvas.create_image(*self._offset,image=photo,anchor='nw')

    def open_server(self):
        if self._server_window is not None and self._server_window.winfo_exists():
            self._server_window.lift();return
        win=self._server_window=tk.Toplevel(self)
        win.title('PlayRobot · Configuración de conexión')
        win.geometry('620x230');win.transient(self.winfo_toplevel())
        box=ttk.Frame(win,padding=22);box.pack(fill='both',expand=True)
        ttk.Label(box,text='URL del servidor de tu escuela').pack(anchor='w')
        entry=ttk.Entry(box,textvariable=self.app._account_server_var)
        entry.pack(fill='x',pady=12);entry.focus_set()
        row=ttk.Frame(box);row.pack(fill='x',pady=7)
        ttk.Button(row,text='Guardar servidor',command=self.app._save_account_server).pack(side='left')
        ttk.Button(row,text='Comprobar conexión',command=self.app._account_test_connection).pack(side='right')
        ttk.Label(box,text='El resultado aparece en la pantalla de acceso.',wraplength=550).pack(anchor='w',pady=12)
