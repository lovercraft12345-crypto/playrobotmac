#define AppVersion "1.0.0"
[Setup]
AppId={{C06AC9B1-23F2-49A8-9567-0E398A3425C6}
AppName=PlayRobot
AppVersion={#AppVersion}
AppPublisher=PlayRobot
DefaultDirName={localappdata}\Programs\PlayRobot
DefaultGroupName=PlayRobot
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
WizardSizePercent=100
WizardImageFile=art\bienvenida.bmp
WizardSmallImageFile=art\cabecera.bmp
SetupIconFile=art\playrobot.ico
UninstallDisplayIcon={app}\app\playrobot.ico
OutputDir=salida
OutputBaseFilename=PlayRobot_Setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
DisableWelcomePage=no
DisableFinishedPage=no
UsePreviousAppDir=yes
SetupLogging=yes
DisableDirPage=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "art\fondo_connect.bmp"; Flags: dontcopy
Source: "stage\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "stage\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PlayRobot"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\playrobot.ico"
Name: "{autodesktop}\PlayRobot"; Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\app\playrobot.ico"; Tasks: desktopicon
Name: "{group}\Desinstalar PlayRobot"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; Description: "Abrir PlayRobot"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Messages]
spanish.WelcomeLabel1=¡Bienvenido a PlayRobot!
spanish.WelcomeLabel2=Arma engranes, aprende programación y crea con tu ESP32.%n%nEste asistente instalará PlayRobot y su entorno de Python. No necesitas instalar Python por separado.%n%nHaz clic en Siguiente para comenzar.
spanish.FinishedHeadingLabel=¡Todo listo para crear!
spanish.FinishedLabel=PlayRobot ya está instalado. Abre el programa desde el escritorio o el menú Inicio.%n%nLesly te espera para comenzar tu próxima aventura.

#include "tema_connect.iss"
