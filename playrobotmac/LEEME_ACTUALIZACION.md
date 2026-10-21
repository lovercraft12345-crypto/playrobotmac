# PlayRobot · Acceso e inicio ilustrados

## Instalador personalizado amarillo

El nuevo tema está en installer/tema_connect.iss y el fondo limpio en installer/art/fondo_connect.bmp. Mantiene controles reales, elección de carpeta, progreso y apertura final. Vuelve a generar el EXE con Crear_Instalador.bat; no reutilices el EXE de la entrega anterior. El diseño usa consejos de programación que cambian con el avance de la instalación.

## Generar instalador gráfico de Windows

Abre installer/LEEME.txt. Crear_Instalador.bat genera installer/salida/PlayRobot_Setup.exe en Windows con Inno Setup 6. Incluye el entorno de Python; los equipos destino no requieren Python. Esta entrega contiene el proyecto de compilación; el EXE aún debe generarse y probarse en Windows.

## Instalar esta versión en tu carpeta actual

1. Cierra la ventana de PlayRobot.
2. Extrae el ZIP en una carpeta aparte.
3. Copia TODO el contenido de su carpeta `playrobot` sobre tu carpeta actual. Incluye los módulos nuevos y la carpeta assets. Acepta reemplazar archivos del programa.
4. Conserva tu `.env`, `playrobot.db` y `.venv`. Este ZIP no los contiene.
5. Abre una terminal en tu carpeta actual y ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe main.py
```

También puedes ejecutar iniciar_windows.bat, que comprueba las dependencias.

Para las cuentas, mantén tu servidor Flask abierto en otra terminal como antes:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Cuenta Premium de demostración

Usuario: admin
Contraseña: admin

En Iniciar sesión escribe admin en Correo o usuario. Abre todos los niveles en el escritorio, incluso sin servidor. Es una cuenta local de pruebas; no modifica las suscripciones ni crea un administrador en el servidor web. Cerrar sesión devuelve el acceso normal.

## Nueva pantalla de acceso

Diseño cálido elegido: Lesly grande a la izquierda, formulario a la derecha, pestañas de inicio de sesión y registro, contraseña visible/oculta y entrada como invitado. Conserva la configuración del servidor y la gestión de Premium.

Copia también el nuevo archivo access_view.py y los recursos de assets/fonts. No basta con reemplazar main.py.

## Inicio basado en la referencia visual

Esta entrega rehace la pantalla de inicio: tarjetas y botones redondeados, sombras, fondo cálido, bienvenida con Lesly grande, detalles ilustrados y la tipografía Lilita One incluida (con su licencia OFL). El texto y los controles se construyen por separado y siguen siendo funcionales.

- Los botones Comenzar abren los tutoriales 1, 2 y 3.
- Mis niveles, Explorar niveles y Ver todos los niveles abren la galería con los seis tutoriales, los niveles 7 y 8 y modo libre.
- Mis proyectos abre tus archivos guardados.
- Productos abre el catálogo; Explorar en 3D abre el visor real.
- El indicador superior muestra Invitado, Mi cuenta o Premium según la sesión.
- Chatear con Lesly abre el chat existente.
- El inicio ajusta toda su composición al tamaño de la ventana. También admite navegación con Tab y Enter.

El taller de engranes conserva las mejoras de la entrega anterior. Para esta actualización copia también home_view.py, ui_theme.py, modern_ui.py, account_ui.py, main.py y los recursos nuevos en assets; lo más sencillo es actualizar el contenido completo de la carpeta playrobot.

## Diseño del taller

- Inicio con menú lateral: Inicio, Mis niveles, Mis proyectos, Productos y Mi cuenta.
- Bienvenida de Lesly, tarjetas de tutoriales y acceso al catálogo/placa 3D.
- Taller con barra superior: Guardar, Abrir, Deshacer, Correr, Detener, Ver código y Ver/Ocultar placa.
- Caja de engranes con desplazamiento y Lesly fija al pie.
- Mesa amplia con fondo de puntos, engranes más grandes y nuevo código de colores.
- Placa 3D a la derecha y salidas de la simulación debajo. El panel de código se abre al pedirlo. Código y placa alternan para conservar espacio.
- Se mantiene el envío USB, oculto hasta pulsar su botón o Alt+E; se conserva el modo paso a paso.
- Las conexiones L293D se abren en una ventana ampliada para que el diagrama sea legible.
- Se conserva la pantalla de acceso inicial con registro, inicio de sesión e invitado.

## Visor 3D

En Windows, utiliza OpenGL cuando el sistema lo permite. La geometría se prepara una vez y se vuelve a dibujar al mover o acercar la placa. Si no puede inicializarse, usa la vista compatible por software. En Linux/macOS la vista compatible es la predeterminada.

La vista compatible conserva las superficies grandes durante el giro, muestra los cuadros terminados sin esperar a que dejes de mover el mouse y recupera todo el detalle al soltarlo. La fluidez final depende del equipo y sus controladores.

El visor es un MODELO DE REFERENCIA: no refleja todavía mediciones o estados reales por USB. Los LED y controles del simulador siguen indicando el resultado del programa de engranes. No se ha modificado la generación MicroPython para la PCB personalizada sin confirmar sus GPIO.

## Proyectos

Guardar crea un archivo `.playrobot` en la ubicación que elijas. Abrir y Mis proyectos permiten elegir ese archivo para continuar en otro momento. Incluye misión, engranes conectados, engranes sueltos, posiciones y parámetros individuales. Los proyectos son locales, no se suben al servidor.

Deshacer recupera hasta 50 estados recientes de edición de la misión actual. Detén la simulación antes de guardar, abrir o deshacer. El acceso Premium sigue comprobándose al abrir o ejecutar niveles de pago; abrir un proyecto no concede Premium.

## Validación de la entrega

Se comprobaron los módulos Python, las pruebas automatizadas del servidor, cuentas, proyectos y modelo 3D. Se abrió la interfaz en un escritorio virtual Linux para recorrer los seis tutoriales, los niveles 7 y 8, modo libre, alternar paneles, ejecutar/detener y deshacer. La aceleración OpenGL de Windows y el envío a hardware requieren la comprobación en tu computadora.
