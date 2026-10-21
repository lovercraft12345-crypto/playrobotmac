#!/bin/bash
set -e
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ]; then echo 'La compilación requiere una Mac.'; exit 1; fi
if [ ! -x .venv-mac/bin/python ]; then python3 -m venv .venv-mac; fi
.venv-mac/bin/python -m pip install -r requirements-desktop.txt pyinstaller
.venv-mac/bin/python macos/build_mac.py
open macos/salida
read -r -p 'Listo. Pulsa Enter para cerrar.'
