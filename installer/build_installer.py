"""Construye en Windows un instalador autónomo; no incorpora claves ni bases de datos."""
from pathlib import Path
import os, shutil, struct, subprocess, sys, zipfile
ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'installer'
STAGE = HERE / 'stage'

def run(*args):
    subprocess.run([str(x) for x in args], check=True)

def compiler():
    candidates = [shutil.which('ISCC.exe')]
    for key in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        base = Path(os.environ.get(key, 'C:/'))
        candidates += [base / 'Inno Setup 6/ISCC.exe', base / 'Programs/Inno Setup 6/ISCC.exe']
    for p in candidates:
        if p and Path(p).is_file(): return Path(p)
    raise RuntimeError('Instala Inno Setup 6 desde https://jrsoftware.org/isdl.php y vuelve a ejecutar Crear_Instalador.bat.')

def main():
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise RuntimeError('Ejecuta este archivo con Python de Windows de 64 bits.')
    iscc = compiler()
    if '--solo-diseno' in sys.argv:
        if not (STAGE / 'runtime/pythonw.exe').is_file() or not (STAGE / 'app/main.py').is_file():
            raise RuntimeError('No está la compilación anterior. Usa Crear_Instalador.bat una vez para preparar todos los archivos.')
        run(iscc, HERE / 'PlayRobot.iss')
        print('LISTO: ' + str(HERE / 'salida/PlayRobot_Setup.exe'), flush=True)
        return
    source = Path(sys.base_prefix)
    for name in ('python.exe', 'pythonw.exe', 'Lib', 'DLLs', 'tcl'):
        if not (source / name).exists():
            raise RuntimeError('Usa Python oficial con Tcl/Tk instalado. Falta: ' + name)
    # Solo se regenera la carpeta temporal de esta compilación.
    if STAGE.exists(): shutil.rmtree(STAGE)
    runtime = STAGE / 'runtime'; runtime.mkdir(parents=True)
    print('1/4 Incluyendo Python y Tkinter...', flush=True)
    ignore = shutil.ignore_patterns('site-packages', '__pycache__', '*.pyc', 'test', 'tests', 'idlelib', 'ensurepip')
    for name in ('Lib', 'DLLs', 'tcl'):
        shutil.copytree(source / name, runtime / name, ignore=ignore)
    for p in source.iterdir():
        if p.is_file() and (p.suffix.lower() in {'.exe', '.dll'} or p.name.startswith('LICENSE')):
            shutil.copy2(p, runtime / p.name)
    print('2/4 Incluyendo dependencias...', flush=True)
    run(sys.executable, '-m', 'pip', 'install', '--ignore-installed', '--prefix', runtime, '-r', ROOT / 'requirements-desktop.txt')
    # Los lanzadores pip guardan rutas absolutas de la máquina de compilación.
    # Conservamos el script de voz para ejecutarlo con el Python ya instalado.
    playback = runtime / 'Scripts/edge-playback.exe'
    if playback.is_file():
        with zipfile.ZipFile(playback) as archive:
            playback.with_suffix('.py').write_bytes(archive.read('__main__.py'))
    app = STAGE / 'app'; app.mkdir()
    for p in ROOT.glob('*.py'): shutil.copy2(p, app / p.name)
    shutil.copytree(ROOT / 'assets', app / 'assets')
    shutil.copy2(HERE / 'art/playrobot.ico', app / 'playrobot.ico')
    shutil.copy2(HERE / 'Ayuda.txt', app / 'Ayuda.txt')
    print('3/4 Comprobando el entorno incluido...', flush=True)
    run(runtime / 'python.exe', '-I', '-c', 'import tkinter, PIL, numpy, serial, mpremote, esptool, edge_tts, sounddevice, OpenGL, pyopengltk; t=tkinter.Tk(); t.withdraw(); t.destroy()')
    print('4/4 Creando PlayRobot_Setup.exe...', flush=True)
    run(iscc, HERE / 'PlayRobot.iss')
    print('\nLISTO: ' + str(HERE / 'salida/PlayRobot_Setup.exe'), flush=True)

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('\nNo se pudo crear el instalador: ' + str(exc), file=sys.stderr)
        sys.exit(1)
