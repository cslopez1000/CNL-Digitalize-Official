#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PythonExecutable,
    [ValidateSet('Core', 'Backend', 'Optimization')][string]$Dependencies = 'Core',
    [string]$ReferenceRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$venvRoot = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvRoot 'Scripts/python.exe'
$buildRoot = Join-Path $projectRoot 'build/windows'

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')" }
}

if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw 'Install CMake and Visual Studio 2022 Build Tools with Desktop development with C++ before running this installer.'
}
if (-not $ReferenceRoot) {
    $ReferenceRoot = Join-Path $projectRoot '../RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI'
}
$ReferenceRoot = (Resolve-Path -LiteralPath $ReferenceRoot).Path
foreach ($required in @('external/glad/src/glad.c', 'external/glm/glm/glm.hpp', 'external/GLFW/deps/nuklear.h')) {
    if (-not (Test-Path -LiteralPath (Join-Path $ReferenceRoot $required))) { throw "Missing native dependency: $ReferenceRoot/$required" }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    if (Test-Path -LiteralPath $venvRoot) { throw 'Existing .venv is incomplete or belongs to another operating system. Use a separate checkout/environment; the installer will not overwrite it.' }
    if ($PythonExecutable) {
        Invoke-Checked -Executable $PythonExecutable -Arguments @('-c', "import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8, 'Python 3.13 64-bit is required'")
        Invoke-Checked -Executable $PythonExecutable -Arguments @('-m', 'venv', $venvRoot)
    } else {
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install Python 3.13 (64-bit) with the Python launcher, or supply -PythonExecutable.' }
        Invoke-Checked -Executable 'py' -Arguments @('-3.13', '-c', "import struct; assert struct.calcsize('P') == 8, '64-bit Python is required'")
        Invoke-Checked -Executable 'py' -Arguments @('-3.13', '-m', 'venv', $venvRoot)
    }
}
Invoke-Checked -Executable $venvPython -Arguments @('-c', "import sys,struct; assert sys.version_info[:2] == (3,13) and struct.calcsize('P') == 8, 'Existing .venv must use Python 3.13 64-bit'")
# Activation also makes the environment available to subsequent shell commands.
. (Join-Path $venvRoot 'Scripts/Activate.ps1')
$requirements = switch ($Dependencies) {
    'Backend' { 'requirements-backend.txt' }
    'Optimization' { 'requirements-optimization.txt' }
    default { 'requirements.txt' }
}
Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'install', '-r', (Join-Path $projectRoot $requirements))
Invoke-Checked -Executable $venvPython -Arguments @('-m', 'pip', 'check')
Invoke-Checked -Executable 'cmake' -Arguments @('-S', $projectRoot, '-B', $buildRoot, '-G', 'Visual Studio 17 2022', '-A', 'x64', "-DPython_EXECUTABLE=$venvPython", "-DCOMBINATION_REFERENCE_ROOT=$ReferenceRoot", '-DCOMBINATION_BUILD_PYTHON=ON')
Invoke-Checked -Executable 'cmake' -Arguments @('--build', $buildRoot, '--config', 'Release', '--', '/m:1', '/nodeReuse:false', '/p:TrackFileAccess=false')
Invoke-Checked -Executable 'ctest' -Arguments @('--test-dir', $buildRoot, '-C', 'Release', '--output-on-failure')
$env:COMBINATION_CHARTS_DIR = Join-Path $buildRoot 'Release'
Invoke-Checked -Executable $venvPython -Arguments @('-B', (Join-Path $projectRoot 'main.py'), '--check')
Write-Host 'Installation complete. Start the integrated CST controller simulation with .\scripts\run.ps1.'
Write-Host 'The full CST UI/control/database migration is still pending.'
