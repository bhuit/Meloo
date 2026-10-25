[CmdletBinding()]
param([switch]$PreviewTest)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$downloads = Join-Path $env:USERPROFILE 'Downloads'
if ($PreviewTest) {
    $source = Join-Path $root 'build\wizard-preview\Meloo-0.4.2-Setup-x64.exe'
    $destination = Join-Path $downloads ('Meloo-Verification-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.exe')
} else {
    $source = Join-Path $root 'dist\Meloo-0.4.2-Setup-x64.exe'
    $destination = Join-Path $downloads 'Meloo-0.4.2-Setup-x64.exe'
    if (Test-Path -LiteralPath $destination) { throw 'Un fichier de ce nom existe deja dans Telechargements.' }
}
Copy-Item -LiteralPath $source -Destination $destination
$hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $hash) { throw 'Copie non conforme.' }
Write-Output "Export : $destination"
if ($PreviewTest) {
    & (Join-Path $PSScriptRoot 'Test-Wizard.ps1') -SetupPath $destination
} else {
    Copy-Item -LiteralPath ($source + '.sha256') -Destination ($destination + '.sha256')
    & (Join-Path $PSScriptRoot 'Test-Installer.ps1') -Setup $destination
}
