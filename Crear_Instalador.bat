@echo off
setlocal
cd /d "%~dp0"
title PlayRobot - Crear instalador
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" installer\build_installer.py
) else (
  py -3 installer\build_installer.py
)
if errorlevel 1 (
  echo.
  echo No se genero el instalador. Revisa el mensaje anterior.
  pause
  exit /b 1
)
start "" "%~dp0installer\salida"
pause
