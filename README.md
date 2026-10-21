# PlayRobot · Taller de Engranes ESP32

Aplicación de escritorio Python/Tkinter y servidor Flask de cuentas y suscripciones.

**Empieza por `LEEME_ACTUALIZACION.md`**, que explica cómo reemplazar los archivos sin perder la configuración ni la cuenta Premium ya probada.

## Inicio rápido (carpeta que ya tiene .env y playrobot.db)

Terminal del servidor:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Otra terminal:

```powershell
.\.venv\Scripts\python.exe main.py
```

En **Mi cuenta**, servidor `http://127.0.0.1:8001` para esta computadora, o la raíz HTTPS pública para otros equipos. La sesión usa la contraseña de PlayRobot, no la contraseña de Mercado Pago.

## Archivos

- `main.py`: aplicación, engranes, Lesly y simulaciones originales, con controles de acceso añadidos.
- `account_ui.py`: registro, inicio de sesión, estado, checkout y actualización de Premium.
- `account_client.py`: cliente HTTP de cuentas y política de tutoriales gratuitos.
- `app.py`: servidor de autenticación, autorización de misiones y suscripciones.
- `assets/`: recursos originales de la aplicación.
- `requirements-server.txt`: dependencias del servidor.
- `requirements-desktop.txt`: dependencias de Lesly y ESP32 para escritorio.
- `requirements.txt`: instala ambos grupos en la computadora de desarrollo.
- `iniciar_windows.bat`: abre la aplicación de escritorio.
- `run_windows.bat`: abre el servidor de cuentas.

## API

| Método y ruta | Función |
| --- | --- |
| GET /health | Estado del servidor |
| POST /api/auth/register | Registro con correo y contraseña de 12+ caracteres |
| POST /api/auth/login | Inicio de sesión |
| GET /api/me | Estado de cuenta y precio mensual configurado |
| POST /api/access | Verifica acceso a la misión; requiere sesión |
| POST /api/billing/checkout | Prepara enlace de autorización de suscripción |
| POST /api/billing/sync | Consulta en Mercado Pago las suscripciones de la cuenta autenticada |
| POST /api/billing/cancel | Cancela una suscripción de la cuenta autenticada |
| POST /webhooks/mercadopago | Verifica firma y procesa eventos de suscripción admitidos |

El cliente envía únicamente el token de sesión de PlayRobot. Las claves de Mercado Pago permanecen en el servidor. Conserva APP_SECRET_KEY fija, el .env y la base existente al actualizar. El paquete se entrega sin claves, cuentas personales, entornos virtuales ni archivos comprimidos antiguos.

La distribución de código Python en los equipos no equivale a DRM. El flujo de interfaz y la autorización API se verifican; la preparación para cobros reales requiere completar pruebas de renovación/rechazo/cancelación y alojamiento HTTPS estable.
