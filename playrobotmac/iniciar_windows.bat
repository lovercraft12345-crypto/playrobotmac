@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -c "import PIL, numpy, OpenGL, pyopengltk, edge_tts, sounddevice, serial, mpremote, esptool" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
exit /b
:error
 echo No se pudo iniciar. Revisa Python y la conexion a Internet.
 pause
 exit /b 1
