#!/bin/bash
set -e
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ]; then echo 'Este iniciador es para macOS.'; exit 1; fi
if ! command -v python3 >/dev/null 2>&1; then
 echo 'Instala Python 3 desde https://www.python.org/downloads/macos/ y vuelve a abrir este archivo.'
 read -r -p 'Pulsa Enter para cerrar.'; exit 1
fi
python3 -c 'import tkinter; t=tkinter.Tk(); t.withdraw(); t.destroy()' || {
 echo 'Necesitas Python con Tkinter. Usa el instalador oficial de python.org.'
 read -r -p 'Pulsa Enter para cerrar.'; exit 1;
}
python3 -m venv .venv-mac
.venv-mac/bin/python -m pip install -r requirements-desktop.txt
printf '\nAbriendo PlayRobot...\n'
.venv-mac/bin/python main.py
