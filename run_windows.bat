@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
  if errorlevel 1 goto error
)
call ".venv\Scripts\python.exe" -m pip install -r requirements-server.txt
if errorlevel 1 goto error
if not exist ".env" (
  echo Falta el archivo .env. Copia .env.example a .env y completa las claves de prueba.
  pause
  exit /b 1
)
call ".venv\Scripts\python.exe" app.py
goto end
:error
echo No se pudo preparar el servidor. Revisa que Python este instalado.
pause
:end
