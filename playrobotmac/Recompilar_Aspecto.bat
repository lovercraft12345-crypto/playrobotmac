@echo off
setlocal
cd /d "%~dp0"
title PlayRobot - Actualizar diseno del instalador
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" installer\build_installer.py --solo-diseno
) else (
  py -3 installer\build_installer.py --solo-diseno
)
if errorlevel 1 (
  echo Revisa el mensaje anterior.
  pause
  exit /b 1
)
start "" "%~dp0installer\salida"
pause
