"""Cliente de cuentas: solo envía el token de sesión de PlayRobot, nunca claves de Mercado Pago."""
from __future__ import annotations
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

FREE_MISSIONS = frozenset({'led', 'motor', 'button_led', 'traffic', 'crossing', 'light'})

class AccountError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def validate_server_url(value: str) -> str:
    if not isinstance(value, str):
        raise AccountError('La dirección del servidor debe ser texto.')
    value = value.strip().rstrip('/')
    try:
        parts = urlsplit(value)
        parts.port
    except ValueError:
        raise AccountError('La dirección del servidor no es válida.') from None
    local = parts.hostname in ('localhost', '127.0.0.1', '::1')
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or (parts.scheme == 'http' and not local) or parts.username or parts.password
            or parts.query or parts.fragment):
        raise AccountError('Usa una URL HTTPS del servidor, o http://127.0.0.1:8001 para pruebas locales.')
    return value


def validate_checkout_url(value: str) -> str:
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.hostname not in ('www.mercadopago.com.mx', 'mercadopago.com.mx')
            or parts.username or parts.password):
        raise AccountError('El servidor no devolvió un enlace de Mercado Pago México válido.')
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AccountClient:
    def __init__(self, base_url: str):
        self.base_url = validate_server_url(base_url)
        self.token = ''
        self.opener = build_opener(NoRedirect())

    def login_demo_admin(self, username: str, password: str) -> bool:
        """Cuenta de demostración del escritorio; nunca autentica en el servidor."""
        if username == 'admin' and password == 'admin':
            self.token = 'local-demo-admin'
            return True
        return False

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if self.token == 'local-demo-admin':
            if (method, path) in {('GET', '/api/me'), ('POST', '/api/billing/sync')}:
                return {'email': 'admin', 'premium': True, 'free_levels': 6,
                        'premium_levels': '7+', 'subscription_status': 'demo_local',
                        'demo_local': True}
            if (method, path) == ('POST', '/api/access'):
                return {'allowed': True, 'premium': True}
            raise AccountError('Esta es una cuenta Premium de demostración local; no realiza pagos.')
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers['Content-Type'] = 'application/json; charset=utf-8'
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=25) as response:
                result = json.loads(response.read(1024 * 1024).decode('utf-8'))
            if not isinstance(result, dict):
                raise AccountError('El servidor devolvió una respuesta inesperada.')
            return result
        except HTTPError as exc:
            try:
                message = json.loads(exc.read(8192).decode('utf-8')).get('error')
            except (ValueError, UnicodeError, AttributeError):
                message = None
            raise AccountError(message or f'El servidor respondió HTTP {exc.code}.', exc.code) from None
        except (URLError, TimeoutError, OSError):
            raise AccountError('No se pudo contactar al servidor. Revisa la dirección y tu conexión.') from None
        except (ValueError, UnicodeError):
            raise AccountError('El servidor no devolvió JSON válido. Revisa su dirección.') from None
