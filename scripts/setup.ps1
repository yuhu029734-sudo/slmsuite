param([switch]$Gpu)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'

function Invoke-CheckedPython {
    param([string]$Executable, [string[]]$PythonArgs)
    & $Executable @PythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw ('Python command failed (exit ' + $LASTEXITCODE + '): ' + ($PythonArgs -join ' '))
    }
}

Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $basePython = $null
        $pythonCandidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
            (Join-Path $env:ProgramFiles 'Python312\python.exe')
        )
        foreach ($candidate in $pythonCandidates) {
            if (Test-Path -LiteralPath $candidate) { $basePython = $candidate; break }
        }
        if (-not $basePython -and (Get-Command py -ErrorAction SilentlyContinue)) {
            $detectedPython = & py -3.12 -c 'import sys; print(sys.executable)'
            if ($LASTEXITCODE -eq 0) { $basePython = $detectedPython }
        }
        if (-not $basePython) {
            throw 'Install Python 3.12 first: winget install -e --id Python.Python.3.12 --source winget'
        }
        Invoke-CheckedPython -Executable $basePython -PythonArgs @('-m', 'venv', '.venv')
    }

    Invoke-CheckedPython -Executable $venvPython -PythonArgs @(
        '-c', 'import sys; assert sys.version_info[:2] == (3, 12), "This setup requires Python 3.12"'
    )
    Invoke-CheckedPython -Executable $venvPython -PythonArgs @('-m', 'pip', 'install', '--upgrade', 'pip')
    $installArgs = @('-m', 'pip', 'install', '-r', 'requirements-dev.txt')
    if (Test-Path -LiteralPath 'requirements-windows-py312.txt') {
        $installArgs += @('-c', 'requirements-windows-py312.txt')
    }
    Invoke-CheckedPython -Executable $venvPython -PythonArgs $installArgs
    if ($Gpu) {
        Invoke-CheckedPython -Executable $venvPython -PythonArgs @(
            '-m', 'pip', 'install', '-r', 'requirements-gpu-cuda13.txt'
        )
    }
    Invoke-CheckedPython -Executable $venvPython -PythonArgs @('-m', 'pip', 'check')
    $checkArgs = @('scripts/check_environment.py')
    if ($Gpu) { $checkArgs += '--require-gpu' }
    Invoke-CheckedPython -Executable $venvPython -PythonArgs $checkArgs
    Write-Host 'Ready. Open this folder in VS Code; select .venv for Python and notebook kernels.'
}
finally {
    Pop-Location
}
