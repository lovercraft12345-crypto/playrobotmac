from pathlib import Path
import platform,plistlib,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'macos'

def run(*args):subprocess.run([str(x) for x in args],check=True,cwd=ROOT)

def main():
    if sys.platform!='darwin':raise RuntimeError('Compila esta aplicación en macOS.')
    import tkinter
    t=tkinter.Tk();t.withdraw();t.destroy()
    out=HERE/'salida';out.mkdir(exist_ok=True)
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir',
          '--name','PlayRobot','--osx-bundle-identifier','mx.playrobot.taller.prueba',
          '--paths',ROOT,'--distpath',out,'--workpath',HERE/'build','--specpath',HERE,
          '--add-data',str(ROOT/'assets')+':assets','--icon',HERE/'PlayRobot.icns',
          '--hidden-import','main','--hidden-import','tkinter',
          '--collect-all','mpremote','--collect-all','esptool','--collect-all','sounddevice',
          '--collect-all','edge_tts','--collect-all','OpenGL',HERE/'entry.py']
    run(*args)
    app=out/'PlayRobot.app'
    info=app/'Contents/Info.plist'
    with info.open('rb') as f:data=plistlib.load(f)
    data['CFBundleDisplayName']='PlayRobot'
    data['NSMicrophoneUsageDescription']='Lesly usa el micrófono cuando activas la opción de escuchar.'
    with info.open('wb') as f:plistlib.dump(data,f)
    # Firma ad hoc para pruebas; no es firma Developer ID ni notarización.
    run('/usr/bin/codesign','--force','--deep','--sign','-',app)
    executable=app/'Contents/MacOS/PlayRobot'
    report=out/'prueba_app.json'
    subprocess.run([str(executable),'--self-test',str(report)],check=True,timeout=60,cwd=ROOT)
    # Comprobar que el ejecutable congelado también ejecuta las utilidades USB.
    for module in ('mpremote','esptool'):
        subprocess.run([str(executable),'-m',module,'--help'],check=True,timeout=45,cwd=ROOT,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    volume=HERE/'dmg-contenido'
    if volume.exists():shutil.rmtree(volume)
    volume.mkdir()
    shutil.copytree(app,volume/'PlayRobot.app',symlinks=True)
    (volume/'Aplicaciones').symlink_to('/Applications',target_is_directory=True)
    shutil.copy2(HERE/'LEEME_MAC.txt',volume/'LEEME_MAC.txt')
    dmg=out/('PlayRobot_Prueba_'+platform.machine()+'.dmg')
    run('/usr/bin/hdiutil','create','-volname','PlayRobot · Prueba','-srcfolder',volume,
        '-ov','-format','UDZO',dmg)
    print('DMG creado:',dmg)

if __name__=='__main__':main()
