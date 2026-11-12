param(
    [string]$PythonExe,
    [switch]$SkipModelDownload
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

if (-not $PythonExe) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs/Python/Python312/python.exe'),
        (Join-Path $env:ProgramFiles 'Python312/python.exe'),
        'C:/Python312/python.exe'
    )
    $pathPython = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pathPython -and $pathPython.Source -notlike '*\WindowsApps\*') {
        $candidates += $pathPython.Source
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            & $candidate -c "import sys, sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 12) and sysconfig.get_platform() == 'win-amd64' else 1)"
            if ($LASTEXITCODE -eq 0) {
                $PythonExe = $candidate
                break
            }
        }
    }
    if (-not $PythonExe) {
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            try {
                $registered = & $launcher.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0) { $PythonExe = $registered }
            }
            catch {
                $PythonExe = $null
            }
        }
    }
}
if (-not $PythonExe) {
    throw 'Install x64 Windows CPython 3.12 or pass -PythonExe with its full path.'
}
& $PythonExe -c "import sys, sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 12) and sysconfig.get_platform() == 'win-amd64' else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Use a native x64 Windows CPython 3.12 interpreter.' }

$venv = Join-Path $repo '.venv-gesture'
$venvPython = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    & $PythonExe -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the gesture virtual environment.' }
}
& $venvPython -c "import sys, sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 12) and sysconfig.get_platform() == 'win-amd64' else 1)"
if ($LASTEXITCODE -ne 0) { throw "The environment at $venv requires native x64 Windows CPython 3.12." }
& $venvPython -m pip install --only-binary=:all: -r (Join-Path $repo 'requirements-gesture.txt')
if ($LASTEXITCODE -ne 0) { throw 'Gesture wheel installation failed. Check access to PyPI and the Windows x64 Python version.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Gesture dependencies conflict in the virtual environment.' }
& $venvPython -c "import cv2, mediapipe, numpy, pythonosc, sounddevice; assert hasattr(mediapipe.tasks.vision, 'HandLandmarker')"
if ($LASTEXITCODE -ne 0) { throw 'One or more gesture dependencies failed to import.' }

$modelDir = Join-Path $repo 'assets/models'
$model = Join-Path $modelDir 'hand_landmarker.task'
if (-not $SkipModelDownload -and -not (Test-Path -LiteralPath $model -PathType Leaf)) {
    New-Item -Path $modelDir -ItemType Directory -Force | Out-Null
    $pending = "$model.download"
    Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task' -OutFile $pending
    if ((Get-Item -LiteralPath $pending).Length -lt 1000000) { throw 'The downloaded model file is incomplete.' }
    Move-Item -LiteralPath $pending -Destination $model
}
if (Test-Path -LiteralPath $model -PathType Leaf) {
    & $venvPython -c 'import mediapipe as mp, sys; mp.tasks.vision.HandLandmarker.create_from_model_path(sys.argv[1]).close()' $model
    if ($LASTEXITCODE -ne 0) { throw "MediaPipe could not load the model at $model." }
}
Write-Host "Gesture environment ready at $venv"
