# PlayRobot para Mac desde GitHub Actions

Este paquete contiene el código completo y el flujo para generar los DMG sin tener una Mac. No contiene un DMG ya compilado ni publica nada automáticamente.

## Subir el proyecto desde Windows

1. Descomprime este ZIP en una carpeta nueva.
2. En GitHub crea un repositorio, por ejemplo `playrobot-mac-prueba`. Puedes elegir **Private** para mantener privado tu código.
3. En el repositorio pulsa **Add file → Upload files**. Si el repositorio está vacío, busca **uploading an existing file**.
4. Sube TODO el contenido descomprimido, incluida la carpeta `.github`.
5. Pulsa **Commit changes**. No subas el ZIP entero: GitHub necesita los archivos extraídos.

La raíz del repositorio debe contener `main.py`, `requirements-desktop.txt`, `assets`, `macos`, `tests` y `.github`. No deben quedar dentro de otra carpeta `playrobot`. El paquete no incluye tus claves ni tu base de datos; no las agregues al repositorio.

## Generar los instaladores

1. Abre la pestaña **Actions** del repositorio.
2. Si GitHub pide habilitar Actions, habilítalo para este repositorio.
3. En el menú izquierdo elige **Crear PlayRobot para Mac**.
4. Pulsa **Run workflow**, selecciona tu rama principal y confirma **Run workflow**.
5. Espera a que los dos trabajos terminen con una marca verde.
6. Abre esa ejecución y baja hasta **Artifacts**.
7. Descarga `PlayRobot-Mac-arm64` y `PlayRobot-Mac-x86_64`.
8. Descomprime esos archivos descargados: dentro está el `.dmg` correspondiente.

Los artefactos se conservan 14 días; descárgalos para guardarlos. El flujo se ejecuta solo cuando pulsas Run workflow. No crea una publicación pública ni una Release.

## Qué archivo compartir

- `PlayRobot_Prueba_arm64.dmg`: Apple Silicon, series M.
- `PlayRobot_Prueba_x86_64.dmg`: Intel.

El usuario abre el DMG y arrastra PlayRobot a Aplicaciones. La aplicación incluye Python y las dependencias, por lo que los destinatarios no necesitan instalarlos. El chat y las funciones de red mantienen su configuración habitual. El servidor de cuentas no se inicia en el equipo del niño.

Es una edición de pruebas con cuenta Premium LOCAL `admin` / `admin`. Retira esa cuenta antes de comercializarla.

## Comprobaciones automáticas

Cada Mac de GitHub instala Python y Tkinter, ejecuta las pruebas, construye la app, abre brevemente la pantalla de acceso y comprueba las ayudas de mpremote/esptool. Después genera el DMG y verifica su integridad y firma ad hoc. `prueba_app.json` y SHA256 acompañan a cada instalador.

Esto no comprueba un dispositivo ESP32 físico, el sonido por altavoces, el micrófono ni una sesión completa con un niño. Tampoco demuestra compatibilidad con todas las versiones de macOS. Estas compilaciones parten de macOS 15; no se promete soporte de macOS anterior.

## Firma y apertura de la prueba

Los paquetes tienen firma ad hoc para pruebas; no están firmados con Developer ID ni notarizados por Apple. No necesitas configurar certificados para esta prueba. macOS puede bloquear la apertura; consulta las indicaciones de Privacidad y seguridad para una app de prueba que reconoces. No desactives Gatekeeper.

## Si falla

Abre el trabajo rojo y el paso que falló. Copia el mensaje de error o comparte una captura. Los archivos `Diagnostico-Mac-*` pueden aportar detalles adicionales.

Si no aparece Run workflow, comprueba que `.github/workflows/mac-prueba.yml` está en la rama principal, exactamente en esa ruta. Los minutos y disponibilidad de ejecutores dependen de tu cuenta de GitHub.

Fuentes de configuración: https://docs.github.com/en/actions/reference/runners/github-hosted-runners y https://formulae.brew.sh/formula/python-tk%403.13
