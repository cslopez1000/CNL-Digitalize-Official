#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Check,
    [switch]$Simulation,
    [switch]$ZMQ,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$AppArguments
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Simulation -and $ZMQ) { throw 'Choose either -Simulation or -ZMQ, not both.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$venvRoot = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvRoot 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Virtual environment missing. Run scripts/install.ps1 first.' }
. (Join-Path $venvRoot 'Scripts/Activate.ps1')
$env:COMBINATION_CHARTS_DIR = Join-Path $projectRoot 'build/windows/Release'
if (-not (Test-Path -LiteralPath $env:COMBINATION_CHARTS_DIR)) { throw 'Native build missing. Run scripts/install.ps1 first.' }
$arguments = @('-B', (Join-Path $projectRoot 'main.py'))
if ($Check) { $arguments += '--check' }
if ($Simulation) { $arguments += '--simulation' }
if ($ZMQ) { $arguments += '--zmq' }
if ($AppArguments) { $arguments += $AppArguments }
& $venvPython @arguments
if ($LASTEXITCODE -ne 0) { throw "Application exited with code $LASTEXITCODE" }
