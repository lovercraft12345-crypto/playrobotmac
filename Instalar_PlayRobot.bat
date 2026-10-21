@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_playrobot.ps1"
if errorlevel 1 (
    echo.
    echo La instalacion no termino. Revisa el mensaje anterior.
    pause
    exit /b 1
)
echo.
echo Instalacion completa. Ya puedes abrir PlayRobot desde el acceso directo.
pause
