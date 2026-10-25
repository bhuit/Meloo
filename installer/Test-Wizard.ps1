param([string]$SetupPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$preview = Join-Path $root 'build\wizard-preview'
$nativeTest = Join-Path $env:LOCALAPPDATA ('Temp\Meloo-Wizard-QA-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $nativeTest -Force | Out-Null
$env:TEMP = $nativeTest
$env:TMP = $env:TEMP
$setup = Join-Path $preview 'Meloo-0.4.2-Setup-x64.exe'
if ($SetupPath) { $setup = $SetupPath }
$app = Join-Path $nativeTest 'app'
function Run-Check([string]$File,[string[]]$Arguments) {
    $p = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $p.WaitForExit(120000)) { throw "Delai de test depasse (PID $($p.Id))" }
    return $p.ExitCode
}
$code = Run-Check $setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="'+$app+'"'),('/LOG="'+$preview+'\install.log"'))
if ($code -ne 0) { throw "Installation test : $code" }
'OK : installation et marqueur'
$code = Run-Check $setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="'+$app+'"'),('/LOG="'+$preview+'\upgrade.log"'))
if ($code -ne 0) { throw "Reinstallation test : $code" }
'OK : reinstallation'
$code = Run-Check (Join-Path $app 'uninstall\unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+$preview+'\uninstall.log"'))
if ($code -ne 0) { throw "Desinstallation test : $code" }
'OK : desinstallation de verification'
