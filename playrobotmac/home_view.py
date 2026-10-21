"""Illustrated, scalable home screen with real interactive navigation.

Cards, controls and text are drawn separately. This is not a screenshot overlay:
account state is live and every action invokes the existing workshop methods.
"""
import math
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageFont
from ui_theme import UI_FONT

ROOT = Path(__file__).resolve().parent / 'assets'
INK, RED, MUTED = '#101c46', '#f10b35', '#68728d'


def gear(draw, cx, cy, radius, color):
    points = []
    for i in range(64):
        a = i*math.pi/32
        r = radius if i % 8 in (1, 2, 3, 4) else radius*.78
        points.append((cx+math.cos(a)*r, cy+math.sin(a)*r))
    draw.polygon(points, fill=color)
    draw.ellipse((cx-radius*.31, cy-radius*.31, cx+radius*.31, cy+radius*.31), fill=(255, 255, 255, 0))


class IllustratedHome(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg='#fbfaf8')
        self.app = app
        self.canvas = tk.Canvas(self, bg='#fbfaf8', highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='both', expand=True)
        self.actions = []
        self._photos = []
        self._draw_id = None
        self._focus_index = -1
        self._scale, self._offset = 1., (0, 0)
        self._sources = self._load_art()
        families = {x.lower() for x in tkfont.families(self)}
        self.heading_font = 'Lilita One' if 'lilita one' in families else UI_FONT
        self.canvas.bind('<Configure>', self._resize)
        self.canvas.bind('<Motion>', self._hover)
        self.canvas.bind('<Button-1>', self._click)
        self.canvas.bind('<Tab>', lambda e: self._focus(1))
        self.canvas.bind('<Shift-Tab>', lambda e: self._focus(-1))
        self.canvas.bind('<Return>', self._activate)
        self.canvas.bind('<space>', self._activate)
        self.bind('<Destroy>', self._destroyed, add='+')

    def _load_art(self):
        art = {}
        with Image.open(ROOT / 'playrobot-logo.png') as source:
            from PIL import ImageChops
            image = source.convert('RGB')
            bbox = ImageChops.difference(image, Image.new('RGB', image.size, 'white')).getbbox()
            art['logo'] = image.crop(bbox).convert('RGBA') if bbox else image.convert('RGBA')
        with Image.open(ROOT / 'lesly-maestra-saludo-hires.png') as source:
            image = source.convert('RGBA')
            art['teacher'] = image.crop((0, 0, image.width, int(image.height*.71)))
        for key in ('front', 'angle'):
            path = ROOT / 'products' / f'board-{key}.png'
            if path.exists():
                with Image.open(path) as image:
                    art[key] = image.convert('RGBA')
        return art

    def _resize(self, _event=None):
        if self._draw_id is not None:
            self.after_cancel(self._draw_id)
        self._draw_id = self.after(35, self._draw)

    def update_account(self):
        self._resize()

    def _destroyed(self, event):
        if event.widget is self and self._draw_id is not None:
            self.after_cancel(self._draw_id)
            self._draw_id = None

    def _xy(self, x, y):
        return self._offset[0]+x*self._scale, self._offset[1]+y*self._scale

    def _text(self, x, y, text, size=20, color=INK, heading=False, width=None, anchor='nw', font_path=None):
        path = Path(font_path) if font_path is not None else ROOT / 'fonts/LilitaOne-Regular.ttf'
        if heading and path.exists() and not any(c in text for c in '↻↺⚙'):
            # Draw headings with the included font on every platform. Oversample
            # for smooth edges instead of depending on installed Windows fonts.
            scale = self._scale*2
            font = ImageFont.truetype(str(path), max(10, round(size*scale)))
            if width:
                lines=[]
                for paragraph in text.split('\n'):
                    line=''
                    for word in paragraph.split():
                        candidate=(line+' '+word).strip()
                        if line and font.getlength(candidate)>width*scale:
                            lines.append(line);line=word
                        else:line=candidate
                    lines.append(line)
                text='\n'.join(lines)
            dummy=ImageDraw.Draw(Image.new('RGBA',(1,1)))
            bbox=dummy.multiline_textbbox((0,0),text,font=font,spacing=round(4*scale))
            image=Image.new('RGBA',(max(1,bbox[2]-bbox[0]+4),max(1,bbox[3]-bbox[1]+4)))
            ImageDraw.Draw(image).multiline_text((2-bbox[0],2-bbox[1]),text,font=font,
                                                 fill=color,spacing=round(4*scale))
            image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
            photo=ImageTk.PhotoImage(image,master=self);self._photos.append(photo)
            self.canvas.create_image(*self._xy(x,y),image=photo,anchor=anchor)
            return
        opts = {'text': text, 'anchor': anchor, 'fill': color,
                'font': (self.heading_font if heading else UI_FONT,
                         -max(9, round(size*self._scale)), 'normal' if heading and self.heading_font != UI_FONT else 'bold' if heading else 'normal')}
        if width is not None:
            opts.update(width=width*self._scale, justify='left')
        self.canvas.create_text(*self._xy(x, y), **opts)

    def _image(self, key, bounds, crop=False):
        if key not in self._sources:
            return
        x, y, w, h = bounds
        image = self._sources[key].copy()
        size = (max(1, round(w*self._scale)), max(1, round(h*self._scale)))
        if crop:
            ratio = max(size[0]/image.width, size[1]/image.height)
            image = image.resize((round(image.width*ratio), round(image.height*ratio)), Image.Resampling.LANCZOS)
            left = max(0, (image.width-size[0])//2)
            image = image.crop((left, 0, left+size[0], size[1]))
        else:
            image.thumbnail(size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image, master=self)
        self._photos.append(photo)
        px, py = self._xy(x+(w-image.width/self._scale)/2, y+(h-image.height/self._scale)/2)
        self.canvas.create_image(px, py, image=photo, anchor='nw')

    def _action(self, name, bounds, callback):
        self.actions.append((name, bounds, callback))

    def _pill(self, x, y, w, h, text, callback, color=RED, foreground='white', size=21):
        self._text(x+w/2, y+h/2-1, text, size, foreground, heading=True, anchor='center')
        self._action(text, (x, y, x+w, y+h), callback)

    def _draw(self):
        self._draw_id = None
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if w < 50 or h < 50:
            return
        self._scale = min(w/1600, h/1000)
        self._offset = ((w-1600*self._scale)/2, (h-1000*self._scale)/2)
        self.canvas.delete('all')
        self.actions.clear()
        self._photos.clear()
        self._background(w, h)
        self._image('logo', (35, 47, 215, 120))
        for i, (name, icon, callback) in enumerate([
            ('Inicio', 'home', lambda: self.canvas.focus_set()),
            ('Mis niveles', 'game', self.app._show_all_levels),
            ('Mis proyectos', 'folder', self.app._open_project),
            ('Productos', 'box', self.app._open_products),
            ('Mi cuenta', 'user', self.app._open_account),
        ]):
            y = 240+i*71
            self._icon(icon, 60, y, RED if i==0 else INK)
            self._text(98, y, name, 20, RED if i==0 else INK, anchor='w')
            self._action(name, (24, y-28, 260, y+29), callback)
        self._text(314, 24, 'Tu taller de ideas', 45, heading=True)
        logged = bool(self.app.account_client.token)
        status = 'Premium' if logged and self.app.account_info.get('premium') else 'Mi cuenta' if logged else 'Invitado'
        self._icon('user', 1420, 48, INK)
        self._text(1448, 47, status+'  ⌄', 18, anchor='w')
        self._action('Mi cuenta', (1392, 20, 1584, 75), self.app._open_account)
        # Hero text is native, so it stays crisp and is not baked into a mockup.
        self._text(336, 132, '¡Vamos a', 88, heading=True)
        self._text(700, 132, 'crear!', 88, RED, heading=True)
        self._text(339, 230, 'Aprende a programar, engrane por engrane.', 27)
        self._pill(340, 282, 315, 65, 'Explorar niveles  ›', self.app._show_all_levels, size=27)
        self._image('teacher', (965, 7, 390, 371), crop=True)
        self._text(1386, 192, '¡Hola!\nSoy Lesly,\ntu guía en\nPlayRobot', 25, heading=True, width=175)
        self._text(298, 398, 'Tus primeros pasos', 39, heading=True)
        self._text(1395, 414, 'Ver todos los niveles  ›', 16, MUTED, anchor='center')
        self._action('Ver todos los niveles', (1268, 391, 1580, 437), self.app._show_all_levels)
        cards = [
            (300, '01 · Enciende un LED', 'Aprende a encender\ny apagar un LED\ncon engranes.', 'led'),
            (722, '02 · Controla motores', 'Haz que tu robot\nse mueva hacia\nadelante y atrás.', 'motor'),
            (1144, '03 · Programa un botón', 'Usa un botón para\nrealizar acciones\ndivertidas.', 'button_led'),
        ]
        for i, (x, title, description, mission) in enumerate(cards):
            self._text(x+20, 470, title, 27, heading=True, width=374)
            self._text(x+20, 518, description, 20, MUTED, width=215)
            self._text(x+57, 610, 'Gratis', 17, heading=True, anchor='center')
            self._image('front', (x+194, 526, 198, 176))
            if i==0:
                self._led_glow(x+292, 548)
            elif i==1:
                self._rotation_arrow(x+345, 533)
                self._rotation_arrow(x+211, 661, reverse=True)
            else:
                self._text(x+365, 552, '●', 35, RED, anchor='center')
                points=[(x+395,599),(x+367,572),(x+355,555),(x+349,556),
                        (x+349,563),(x+367,586),(x+361,584),(x+356,589),
                        (x+361,601),(x+380,615),(x+394,611)]
                self.canvas.create_polygon(*[v for pt in points for v in self._xy(*pt)],
                                            fill='#ffe4cd',outline=INK,width=2*self._scale,
                                            smooth=True,splinesteps=12)
            self._pill(x+20, 641, 165, 47, 'Comenzar  ›', lambda m=mission: self.app._select_mission(m), size=20)
            self._action(title, (x+190, 512, x+396, 705), lambda m=mission: self.app._select_mission(m))
        self._text(326, 764, 'Conoce tu placa PlayRobot', 39, heading=True)
        self._text(327, 820, 'Explora todos sus componentes y descubre\nlo que puedes hacer con ella.', 21, MUTED)
        self._pill(329, 899, 248, 57, 'Explorar en 3D  ›', self.app._open_board_viewer, size=24)
        self._image('angle', (1000, 715, 372, 266))
        self._text(1437, 879, 'La placa\nPlayRobot', 24, heading=True, width=145)
        self._text(657, 914, 'Sensores\nintegrados', 14)
        self._text(790, 914, '</>', 26, '#00bdeb')
        self._text(844, 914, 'Compatible\ncon engranes', 14)
        self._action('Placa PlayRobot', (996, 725, 1575, 979), self.app._open_board_viewer)
        # Fixed lower-left chat launcher; never overlaps the workspace.
        self._image('teacher', (16, 796, 133, 113), crop=True)
        self._text(158, 802, '¡Hola!\nSoy Lesly,\n¿en qué puedo\nayudarte?', 15)
        self._pill(29, 914, 227, 49, 'Chatear con Lesly', self.app._open_lesly_class, size=18)
        self._action('Preguntar a Lesly', (16, 789, 258, 909), self.app._open_lesly_class)
        self._draw_focus()

    def _background(self, width, height):
        # Pillow is used for native UI surfaces (rounded shapes, gradient, shadow),
        # never to display a flattened screenshot in place of functioning controls.
        scale = self._scale
        layer = Image.new('RGBA', (1600, 1000), '#fbfaf8')
        shadows = Image.new('RGBA', layer.size)
        d = ImageDraw.Draw(shadows)
        for box in [(10, 10, 274, 986), (298, 735, 1584, 983)]:
            d.rounded_rectangle((box[0], box[1]+5, box[2], box[3]+5), 23, fill=(30, 40, 65, 17))
        layer.alpha_composite(shadows.filter(ImageFilter.GaussianBlur(12)))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((10, 10, 274, 986), 24, fill='white')
        d.rounded_rectangle((24, 211, 260, 270), 17, fill='#fff0f2')
        d.rounded_rectangle((1392, 20, 1584, 75), 30, fill='#f6f7fb', outline='#e1e4ec', width=2)
        hero = Image.new('RGBA', (1286, 291))
        hd = ImageDraw.Draw(hero)
        for x in range(hero.width):
            t = abs(x/hero.width-.5)*2
            hd.line((x, 0, x, hero.height), fill=(255, round(229+t*9), round(137+t*26), 255))
        mask = Image.new('L', hero.size); ImageDraw.Draw(mask).rounded_rectangle((0, 0,1286,291),24,fill=255)
        hero.putalpha(mask); layer.alpha_composite(hero,(298,88))
        decorations = Image.new('RGBA', layer.size); gd = ImageDraw.Draw(decorations)
        for x, y, r in [(1404,161,56),(931,308,59),(821,342,35)]:gear(gd,x,y,r,(249,190,49,65))
        for x, y, r in [(1021,800,48),(1551,798,44)]:gear(gd,x,y,r,(210,216,225,65))
        layer.alpha_composite(decorations)
        d = ImageDraw.Draw(layer)
        for i, x in enumerate((300,722,1144)):
            d.rounded_rectangle((x,454,x+404,708),20,fill=('#fff0f2','#eaf6ff','#effaf4')[i],
                                outline=('#fbe4e8','#e0effa','#e2f2e8')[i],width=2)
            d.rounded_rectangle((x+20,592,x+94,628),15,fill='#ffe478')
            d.rounded_rectangle((x+20,641,x+185,688),23,fill=RED)
        d.rounded_rectangle((298,735,1584,983),22,fill='white')
        tiny_decor=Image.new('RGBA',layer.size);tiny_draw=ImageDraw.Draw(tiny_decor)
        gear(tiny_draw,628,931,18,(246,190,0,255))
        gear(tiny_draw,1012,803,45,(218,223,232,85))
        gear(tiny_draw,1553,794,43,(218,223,232,85))
        layer.alpha_composite(tiny_decor)
        d=ImageDraw.Draw(layer)
        d.polygon([(1500,329),(1490,321),(1487,316),(1489,311),(1493,309),
                   (1500,314),(1506,309),(1511,311),(1513,316),(1510,322)],fill=RED)
        d.rounded_rectangle((340,282,655,347),32,fill=RED)
        d.rounded_rectangle((329,899,577,956),29,fill=RED)
        d.rounded_rectangle((144,782,262,894),22,fill='white',outline='#e5e8f0',width=2)
        d.rounded_rectangle((29,914,256,963),22,fill=RED)
        # Add a few small warm accents without obscuring any text.
        for x,y in ((942,127),(1548,208),(1370,303),(1363,802)):
            d.line((x,y,x+14,y-23),fill='#ffbe00',width=7)
        image = layer.resize((max(1,round(1600*scale)),max(1,round(1000*scale))),Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image,master=self); self._photos.append(photo)
        self.canvas.create_image(*self._offset,image=photo,anchor='nw')

    def _icon(self, name, x, y, color):
        def line(points, width=3):
            self.canvas.create_line(*[v for pair in points for v in self._xy(*pair)], fill=color,
                                    width=max(1,width*self._scale), capstyle='round', joinstyle='round')
        def rect(a,b,c,d,fill=''):
            self.canvas.create_rectangle(*self._xy(a,b),*self._xy(c,d),outline=color,fill=fill,width=2*self._scale)
        if name=='user':
            self.canvas.create_oval(*self._xy(x-7,y-14),*self._xy(x+7,y),fill=color,outline='')
            self.canvas.create_arc(*self._xy(x-12,y+1),*self._xy(x+12,y+23),start=0,extent=180,fill=color,outline='',style='pieslice')
        elif name=='home':
            line([(x-13,y-1),(x,y-13),(x+13,y-1)])
            rect(x-10,y-1,x+10,y+12,color)
        elif name=='folder':
            rect(x-13,y-6,x+14,y+12,color);rect(x-13,y-12,x-2,y-4,color)
        elif name=='box':
            line([(x,y-14),(x+13,y-6),(x+13,y+8),(x,y+16),(x-13,y+8),(x-13,y-6),(x,y-14)])
            line([(x-13,y-6),(x,y+1),(x+13,y-6)]);line([(x,y+1),(x,y+16)])
        else:
            line([(x-13,y+10),(x-10,y-7),(x+10,y-7),(x+13,y+10)],7)
            line([(x-8,y),(x-1,y)],2);line([(x-4,y-4),(x-4,y+4)],2)

    def _led_glow(self,x,y):
        self.canvas.create_oval(*self._xy(x-10,y-13),*self._xy(x+10,y+13),fill=RED,outline='#ff747a',width=4*self._scale)
        self.canvas.create_oval(*self._xy(x-4,y-8),*self._xy(x+2,y-1),fill='white',outline='')

    def _rotation_arrow(self,x,y,reverse=False):
        points=[]
        for i in range(23):
            angle=(i/22*2.4+(2.8 if reverse else 4.2))
            points.extend(self._xy(x+math.cos(angle)*25,y+math.sin(angle)*20))
        if reverse:
            points=[v for i in range(len(points)-2,-1,-2) for v in points[i:i+2]]
        self.canvas.create_line(*points,fill='#00baeb',width=max(3,7*self._scale),
                                smooth=True,arrow=tk.LAST,
                                arrowshape=(15*self._scale,18*self._scale,8*self._scale))

    def _at(self,event):
        x=(event.x-self._offset[0])/self._scale; y=(event.y-self._offset[1])/self._scale
        return next((i for i,(_,b,_) in enumerate(self.actions) if b[0]<=x<=b[2] and b[1]<=y<=b[3]),None)

    def _hover(self,event):
        self.canvas.configure(cursor='hand2' if self._at(event) is not None else '')

    def _click(self,event):
        index=self._at(event)
        if index is not None:
            self._focus_index=index
            self.canvas.focus_set()
            self.actions[index][2]()

    def _focus(self,direction):
        if self.actions:
            self._focus_index=(self._focus_index+direction)%len(self.actions)
            self._draw_focus()
        return 'break'

    def _draw_focus(self):
        self.canvas.delete('focus-ring')
        if 0<=self._focus_index<len(self.actions):
            _,b,_=self.actions[self._focus_index]
            self.canvas.create_rectangle(*self._xy(b[0],b[1]),*self._xy(b[2],b[3]),
                                         outline='#1676de',width=2,tags='focus-ring')

    def _activate(self,_event=None):
        if 0<=self._focus_index<len(self.actions):self.actions[self._focus_index][2]()
        return 'break'
