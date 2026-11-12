param([string]$PythonExe)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $gesturePython = Join-Path $repo '.venv-gesture/Scripts/python.exe'
    if (Test-Path -LiteralPath $gesturePython -PathType Leaf) {
        $PythonExe = $gesturePython
    }
    else {
        $PythonExe = (Get-Command python.exe -ErrorAction Stop).Source
    }
}

Push-Location $repo
try {
    & $PythonExe -m unittest discover -s tests -v
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
