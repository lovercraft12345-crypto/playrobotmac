$ErrorActionPreference = 'Stop'

$pythonVersion = '3.13.15'
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$pythonSha256 = 'edec09c4853aeae9ac36efb8c9f95b6b8e2fee65eee56d9767a8b7c69c574403'
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\PlayRobot'
$appDir = Join-Path $installRoot 'app'
$pythonDir = Join-Path $installRoot 'Python'
$venvDir = Join-Path $installRoot 'entorno'
$pythonExe = Join-Path $pythonDir 'python.exe'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$venvPythonW = Join-Path $venvDir 'Scripts\pythonw.exe'

function Write-Step([string]$message) {
    Write-Host "`n$message" -ForegroundColor Cyan
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'Esta version necesita Windows de 64 bits.'
    }
    if (-not (Test-Path (Join-Path $PSScriptRoot 'main.py'))) {
        throw 'No encuentro main.py. Extrae primero todo el ZIP y ejecuta este instalador desde la carpeta PlayRobot_ESP32.'
    }

    New-Item -ItemType Directory -Force -Path $installRoot | Out-Null

    if (-not (Test-Path $pythonExe)) {
        Write-Step 'Descargando Python oficial…'
        $installer = Join-Path $env:TEMP "python-$pythonVersion-amd64.exe"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installer
        $actualHash = (Get-FileHash -Path $installer -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $pythonSha256) {
            Remove-Item -Force $installer -ErrorAction SilentlyContinue
            throw 'La descarga de Python no pasó la comprobación de seguridad. No se instaló.'
        }

        Write-Step 'Instalando Python en tu usuario…'
        $pythonArgs = @(
            '/passive',
            'InstallAllUsers=0',
            'PrependPath=0',
            'Include_launcher=0',
            'Include_pip=1',
            'Include_tcltk=1',
            'Include_test=0',
            "TargetDir=`"$pythonDir`""
        )
        $pythonInstall = Start-Process -FilePath $installer -ArgumentList $pythonArgs -Wait -PassThru
        if ($pythonInstall.ExitCode -ne 0 -or -not (Test-Path $pythonExe)) {
            throw "No se pudo instalar Python (código $($pythonInstall.ExitCode))."
        }
        Remove-Item -Force $installer -ErrorAction SilentlyContinue
    }

    Write-Step 'Copiando PlayRobot y sus recursos…'
    New-Item -ItemType Directory -Force -Path $appDir | Out-Null
    Get-ChildItem -LiteralPath $PSScriptRoot -Force |
        Where-Object { $_.Name -notin @('Instalar_PlayRobot.bat', 'instalar_playrobot.ps1', '.env', '.venv', '__pycache__', 'playrobot.db', 'tests', 'app.py') } |
        Copy-Item -Destination $appDir -Recurse -Force

    $envFile = Join-Path $appDir '.env'
    $envExample = Join-Path $appDir '.env.desktop.example'
    if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
        Copy-Item $envExample $envFile
    }

    if (-not (Test-Path $venvPython)) {
        Write-Step 'Preparando el entorno privado de PlayRobot…'
        & $pythonExe -m venv $venvDir
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
            throw 'No se pudo preparar el entorno de Python.'
        }
    }

    Write-Step 'Instalando automáticamente las dependencias…'
    & $venvPython -m pip install --disable-pip-version-check --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar pip. Revisa la conexión a internet.' }
    & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $appDir 'requirements-desktop.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se instalaron todas las dependencias. Revisa la conexión a internet y vuelve a ejecutar Instalar_PlayRobot.bat.' }

    Write-Step 'Creando accesos directos…'
    $shell = New-Object -ComObject WScript.Shell
    $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\PlayRobot'
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
    foreach ($shortcutPath in @(
        (Join-Path $startMenu 'PlayRobot.lnk'),
        (Join-Path ([Environment]::GetFolderPath('Desktop')) 'PlayRobot.lnk')
    )) {
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $venvPythonW
        $shortcut.Arguments = '"' + (Join-Path $appDir 'main.py') + '"'
        $shortcut.WorkingDirectory = $appDir
        $shortcut.Description = 'Taller de Engranes PlayRobot para ESP32'
        $shortcut.Save()
    }

    Write-Step '¡PlayRobot quedó instalado! Abriendo el programa…'
    Start-Process -FilePath $venvPythonW -ArgumentList ('"' + (Join-Path $appDir 'main.py') + '"') -WorkingDirectory $appDir
    exit 0
}
catch {
    Write-Host "`nNo se pudo completar la instalación:`n$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
