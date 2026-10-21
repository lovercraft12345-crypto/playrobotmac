#!/bin/bash
set -e
cd "$(dirname "$0")/.."
if [ ! -x .venv-mac/bin/python ]; then
 exec /bin/bash macos/Preparar_Prueba.command
fi
exec .venv-mac/bin/python main.py
