param(
    [ValidateSet('VISION', 'AUDIO+VISION', 'AUDIO_ONLY', 'KEYBOARD')]
    [string]$Mode = 'VISION',
    [ValidateRange(0, 64)]
    [Nullable[int]]$Camera,
    [ValidateRange(0, 256)]
    [Nullable[int]]$Microphone,
    [string]$Config,
    [ValidateRange(1, 65535)]
    [int]$Port = 7400,
    [ValidateRange(15, 120)]
    [Nullable[int]]$Fps,
    [ValidateSet('auto', 'dshow', 'msmf', 'any')]
    [string]$Backend,
    [switch]$Preview,
    [switch]$Diagnostics
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv-gesture/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Run scripts/setup_windows.ps1 to install the gesture worker first.'
}
$launchArgs = @('-m', 'gesture_service.main', '--mode', $Mode, '--port', $Port)
if ($null -ne $Camera) { $launchArgs += @('--camera', $Camera) }
if ($null -ne $Microphone) { $launchArgs += @('--microphone', $Microphone) }
if ($null -ne $Fps) { $launchArgs += @('--fps', $Fps) }
if ($Backend) { $launchArgs += @('--backend', $Backend) }
if ($Preview) { $launchArgs += '--preview' }
if ($Diagnostics) { $launchArgs += '--diagnostics' }
if ($Config) { $launchArgs += @('--config', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Config)) }
Push-Location $repo
try {
    & $python @launchArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
