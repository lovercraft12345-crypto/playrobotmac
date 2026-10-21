"""Ventana de cuentas Tkinter; las peticiones de red se ejecutan fuera del hilo gráfico."""
from __future__ import annotations
import json
import os
import queue
import re
import threading
import tkinter as tk
from ui_theme import UI_FONT
import webbrowser
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog
from account_client import AccountClient, AccountError, FREE_MISSIONS, validate_server_url, validate_checkout_url


class AccountMixin:
    def _init_account(self):
        self._workshop_started = False
        self._account_config = Path.home() / '.playrobot' / 'servidor.json'
        url = os.getenv('PLAYROBOT_API_URL', 'http://127.0.0.1:8001')
        try:
            config = json.loads(self._account_config.read_text(encoding='utf-8'))
            url = config.get('server_url', url)
            self._account_remembered_email = config.get('last_email', '')
        except (OSError, ValueError, AttributeError):
            pass
        try:
            self.account_client = AccountClient(url)
        except AccountError:
            self.account_client = AccountClient('http://127.0.0.1:8001')
        self.account_info = {}
        self.account_window = None
        self._account_busy = False
        self._account_queue = queue.Queue()
        self._account_generation = 0
        self._checkout_url = None
        self._premium_buttons = []
        self._account_poll_id = None
        self.after(100, self._drain_account_queue)

    def _drain_account_queue(self):
        try:
            while True:
                generation, callback, result, error = self._account_queue.get_nowait()
                if generation != self._account_generation:
                    continue
                self._account_busy = False
                if error is not None:
                    if isinstance(error, AccountError) and error.status == 401:
                        self.account_client.token = ''
                        self.account_info = {}
                        self._checkout_url = None
                        self._paint_account()
                    self._set_account_message(str(error))
                    parent = self.account_window if self.account_window is not None and self.account_window.winfo_exists() else self
                    messagebox.showwarning('Mi cuenta', str(error), parent=parent)
                else:
                    callback(result)
        except queue.Empty:
            pass
        self.after(100, self._drain_account_queue)

    def _account_async(self, operation, callback, message='Consultando el servidor…'):
        if self._account_busy:
            self._set_account_message('Espera a que termine la consulta actual.')
            return
        self._account_busy = True
        self._set_account_message(message)
        generation = self._account_generation
        def worker():
            try:
                result, error = operation(), None
            except Exception as exc:
                result, error = None, exc if isinstance(exc, AccountError) else AccountError('No se pudo completar la consulta.')
            self._account_queue.put((generation, callback, result, error))
        threading.Thread(target=worker, daemon=True).start()

    def _set_account_message(self, text):
        view = getattr(self, '_account_view', None)
        if view is not None and view.winfo_exists():
            view.set_message(text, self._account_busy)

    def _account_home_bar(self, parent):
        self._premium_buttons = []
        self._account_home_button = tk.Button(
            parent, text='Mi cuenta · Invitado', command=self._open_account,
            bg='#eaf3ff', fg='#173657', relief='flat', padx=12, pady=9,
            font=(UI_FONT, 10, 'bold'), cursor='hand2')
        self._account_home_button.pack(side='right', padx=8, pady=20)
        self._paint_account()

    @staticmethod
    def _mission_is_free(mission, challenge=None):
        return mission in FREE_MISSIONS and challenge is None

    def _paint_account(self):
        home = getattr(self, 'home_view', None)
        if home is not None and home.winfo_exists() and getattr(self, 'on_home_screen', False):
            home.update_account()
        premium = self.account_info.get('premium') is True and bool(self.account_client.token)
        label = 'Premium' if premium else 'Cuenta gratuita' if self.account_client.token else 'Invitado'
        button = getattr(self, '_account_home_button', None)
        if button is not None and button.winfo_exists():
            button.configure(text='Mi cuenta · ' + label)
        for button in self._premium_buttons:
            if button.winfo_exists():
                button.configure(text='Elegir misión →' if premium else 'Premium · Ver acceso →')
        view = getattr(self, '_account_view', None)
        if view is not None and view.winfo_exists():
            view.refresh()

    def _open_account(self):
        if self.account_window is not None and self.account_window.winfo_exists():
            self.account_window.lift()
            return
        from access_view import AccessView
        win = self.account_window = tk.Toplevel(self)
        win.title('PlayRobot · Bienvenido a tu taller')
        width = min(1540, self.winfo_screenwidth()-40)
        height = min(970, self.winfo_screenheight()-75)
        win.geometry(f'{width}x{height}+{max(0,(self.winfo_screenwidth()-width)//2)}+{max(0,(self.winfo_screenheight()-height)//2)}')
        win.minsize(min(1000,width), min(650,height))
        win.configure(bg='#fffdf9')
        if self._workshop_started:
            win.transient(self)
        win.protocol('WM_DELETE_WINDOW', self._close_account_panel)
        self._account_view = AccessView(win, self)
        self._account_view.pack(fill='both', expand=True)
        win.bind('<Return>', self._account_enter)
        win.bind('<Escape>', lambda _e: self._close_account_panel())
        self._paint_account()
        if self._account_busy:
            self._set_account_message('Consultando tu cuenta…')
        elif self.account_client.token:
            self._refresh_account()
        else:
            self._account_view.focus_email()

    def _toggle_account_password(self):
        for entry in self._account_password_entries:
            entry.configure(show='' if self._account_show_password.get() else '•')

    def _account_enter(self, _event=None):
        view = getattr(self, '_account_view', None)
        if view is not None and view.winfo_exists():
            view.submit()
        return 'break'

    def _close_account_panel(self):
        if not self._workshop_started:
            self.destroy()
            return
        if self.account_window is not None and self.account_window.winfo_exists():
            self._account_password_var.set('')
            self._account_confirm_var.set('')
            self.account_window.destroy()
        self.account_window = None

    def _enter_workshop(self):
        # Guests have no session token and retain access to the six free tutorials.
        if not self._workshop_started:
            self._workshop_started = True
            self._build_start_screen()
            self.deiconify()
            self._update_lesly_tips()
        self._close_account_panel()
        self.lift()

    def _toggle_account_server(self):
        view = getattr(self, '_account_view', None)
        if view is not None and view.winfo_exists():
            view.open_server()

    def _account_access_help(self):
        messagebox.showinfo('Ayuda para entrar',
            'Usa el correo y la contraseña que registraste en PlayRobot.\n\n'
            'Si no tienes cuenta, abre Crear cuenta.\n'
            'Si olvidaste tu contraseña, pide al responsable del taller que restablezca tu acceso.\n'
            'Si no conecta, revisa Configuración de conexión.\n\n'
            'Puedes continuar con los seis tutoriales gratuitos.', parent=self.account_window)

    def _account_test_connection(self):
        try:
            client = AccountClient(self._account_server_var.get())
        except AccountError as exc:
            self._set_account_message(str(exc))
            return
        def checked(info):
            if info.get('ok') is True and info.get('service') == 'PlayRobot Suscripciones':
                self._set_account_message('Conexión correcta con PlayRobot. Guarda la dirección si la cambiaste.')
            else:
                self._set_account_message('La dirección responde, pero no corresponde al servidor de cuentas PlayRobot.')
        self._account_async(lambda: client.request('GET', '/health'), checked, 'Comprobando la conexión…')

    def _save_account_server(self):
        if self._account_busy:
            self._set_account_message('Espera a que termine la consulta antes de cambiar el servidor.')
            return
        try:
            url = validate_server_url(self._account_server_var.get())
            self._account_config.parent.mkdir(parents=True, exist_ok=True)
            self._account_config.write_text(json.dumps({'server_url': url, 'last_email': getattr(self, '_account_remembered_email', '')}), encoding='utf-8')
        except (OSError, AccountError) as exc:
            messagebox.showwarning('Servidor', str(exc), parent=self.account_window)
            return
        if url != self.account_client.base_url:
            self._account_logout()
            self.account_client = AccountClient(url)
        self._set_account_message('Servidor guardado. Inicia sesión con tu cuenta de PlayRobot.')

    def _account_auth(self, mode):
        if self._account_busy:
            return
        username = self._account_email_var.get().strip()
        if mode == 'login' and username == 'admin':
            if not self.account_client.login_demo_admin(username, self._account_password_var.get()):
                self._set_account_message('Contraseña incorrecta para admin.')
                return
            self._account_password_var.set('')
            self._account_confirm_var.set('')
            self._checkout_url = None
            self._refresh_account(enter_workshop=True)
            return
        try:
            if validate_server_url(self._account_server_var.get()) != self.account_client.base_url:
                raise AccountError('Primero pulsa Guardar servidor.')
        except AccountError as exc:
            messagebox.showwarning('Servidor', str(exc), parent=self.account_window)
            return
        email = self._account_email_var.get().strip()
        password = self._account_password_var.get()
        if not email or not password:
            self._set_account_message('Escribe el correo y la contraseña de PlayRobot.')
            return
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            self._set_account_message('Revisa el correo: debe tener un formato como nombre@dominio.com.')
            return
        if mode == 'register':
            if len(password) < 12:
                self._set_account_message('La contraseña debe tener al menos 12 caracteres.')
                return
            confirm = self._account_confirm_var.get()
            if confirm != password:
                self._set_account_message('Las contraseñas no coinciden.')
                return
        client = self.account_client
        def operation():
            result = client.request('POST', '/api/auth/' + mode, {'email': email, 'password': password})
            return result
        def finished(result):
            client.token = result['token']
            self._account_password_var.set('')
            self._account_confirm_var.set('')
            self._account_remembered_email = email if self._account_remember_var.get() else ''
            try:
                self._account_config.parent.mkdir(parents=True, exist_ok=True)
                self._account_config.write_text(json.dumps({
                    'server_url': client.base_url, 'last_email': self._account_remembered_email
                }), encoding='utf-8')
            except OSError:
                pass
            self._checkout_url = None
            self._refresh_account(enter_workshop=True)
        self._account_async(operation, finished, 'Entrando a tu cuenta…')

    def _refresh_account(self, sync=False, enter_workshop=False):
        if not self.account_client.token:
            self._open_account()
            return
        client = self.account_client
        def finished(info):
            self.account_info = info
            self._paint_account()
            self._set_account_message('Premium activo. Ya puedes abrir los niveles avanzados.' if info.get('premium') else 'Cuenta actualizada. Tutoriales 1–6 disponibles; Premium aún no está activo.')
            if enter_workshop:
                self._enter_workshop()
        self._account_async(
            lambda: client.request('POST', '/api/billing/sync', {}) if sync else client.request('GET', '/api/me'),
            finished, 'Verificando el estado de tu cuenta…')

    def _account_logout(self):
        self._account_generation += 1
        self._account_busy = False
        self.account_client.token = ''
        self.account_info = {}
        self._checkout_url = None
        if self._account_poll_id is not None:
            self.after_cancel(self._account_poll_id)
            self._account_poll_id = None
        if not self.on_home_screen and not self._mission_is_free(self.mission, self.active_challenge):
            self._go_home()
        self._paint_account()
        self._set_account_message('Sesión cerrada. Los seis tutoriales siguen disponibles.')

    def _require_mission_access(self, mission, challenge, on_allowed):
        if not self.account_client.token:
            self._open_account()
            self._set_account_message('Inicia sesión para consultar tu acceso a este nivel Premium.')
            return
        client = self.account_client
        def finished(result):
            if result.get('allowed') is True:
                on_allowed()
            else:
                self.account_info['premium'] = False
                self._paint_account()
                self._open_account()
                self._set_account_message('Este nivel requiere Premium. Puedes seguir usando los tutoriales 1–6 gratis.')
        self._account_async(lambda: client.request('POST', '/api/access', {
            'mission': mission, 'challenge': challenge is not None}), finished)

    def _account_checkout(self):
        if not self.account_client.token:
            self._set_account_message('Primero inicia sesión.')
            return
        if self._checkout_url:
            webbrowser.open(self._checkout_url)
            self._set_account_message('Se abrió el enlace pendiente. Después pulsa Ya pagué · Actualizar Premium.')
            return
        client = self.account_client
        def offer(info):
            if info.get('premium'):
                self.account_info = info
                self._paint_account()
                self._set_account_message('Ya tienes Premium activo.')
                return
            price = info.get('premium_monthly_price_mxn', 99)
            mode = info.get('billing_mode', 'test')
            email = simpledialog.askstring('Correo de pago',
                'Correo de tu cuenta de Mercado Pago' + (' COMPRADORA DE PRUEBA' if mode == 'test' else '') + ':',
                initialvalue=info.get('email', ''), parent=self.account_window)
            if not email:
                self._set_account_message('No se creó un enlace de pago.')
                return
            if not messagebox.askokcancel('PlayRobot Premium',
                f'Suscripción mensual: ${price} MXN.\n' +
                ('Prueba: usa exclusivamente cuentas y saldo de prueba.\n' if mode == 'test' else '') +
                'Se abrirá Mercado Pago. Ahí revisas y autorizas la suscripción.\n¿Continuar?', parent=self.account_window):
                return
            def checkout_done(result):
                try:
                    url = validate_checkout_url(result['checkout_url'])
                except (AccountError, KeyError) as exc:
                    self._set_account_message(str(exc))
                    return
                self._checkout_url = url
                webbrowser.open(url)
                self._set_account_message('Completa la autorización en Mercado Pago y pulsa Ya pagué · Actualizar Premium.')
                self._account_watch_payment(6)
            self._account_async(lambda: client.request('POST', '/api/billing/checkout', {'payer_email': email.strip()}), checkout_done, 'Preparando el enlace de Mercado Pago…')
        self._account_async(lambda: client.request('GET', '/api/me'), offer)

    def _account_watch_payment(self, remaining):
        def poll():
            self._account_poll_id = None
            if not self.account_client.token or self.account_info.get('premium'):
                return
            if self._account_busy:
                self._account_watch_payment(remaining)
                return
            self._refresh_account()
            if remaining > 1:
                self._account_watch_payment(remaining - 1)
        self._account_poll_id = self.after(15000, poll)
