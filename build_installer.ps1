[CmdletBinding()]
param(
    [string]$Compiler = (Join-Path $PSScriptRoot 'tools\InnoSetup\ISCC.exe'),
    [string]$Payload = (Join-Path $PSScriptRoot 'dist\Zeste')
)
$ErrorActionPreference = 'Stop'
$Payload = (Resolve-Path -LiteralPath $Payload).Path
$marker = Get-Content -LiteralPath (Join-Path $Payload '.zeste-generated.json') -Raw | ConvertFrom-Json
if ($marker.product -ne 'zeste-windows-portable' -or $marker.version -ne '0.4.2') {
    throw 'La distribution complete Meloo 0.4.2 validee est requise.'
}
foreach ($entry in $marker.source_sha256.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $entry.Name) -Algorithm SHA256).Hash
    if ($actual -ne $entry.Value) { throw "Source modifiee depuis la validation : $($entry.Name)" }
}
foreach ($relative in @('Meloo.exe','_internal\python312.dll','tools\LibreOffice\program\soffice.exe','tools\share\Zeste.Share.exe','LICENSE.txt','NOTICE.txt','source\main.py','validation\delivery.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Payload $relative))) { throw "Composant absent : $relative" }
}
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Compilateur Inno Setup 7 manquant. Voir installer\README.txt.' }
$output = Join-Path $PSScriptRoot 'dist'
$scratch = Join-Path $PSScriptRoot 'build\installer-tmp'
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
try {
    $env:TEMP = $scratch
    $env:TMP = $scratch
    & $Compiler '/Qp' "/DAppVersion=$($marker.version)" "/DPayloadDir=$Payload" "/DOutputFolder=$output" (Join-Path $PSScriptRoot 'installer\Meloo.iss')
    if ($LASTEXITCODE -ne 0) { throw "Echec Inno Setup : $LASTEXITCODE" }
    $setup = Join-Path $output "Meloo-$($marker.version)-Setup-x64.exe"
    $hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $([IO.Path]::GetFileName($setup))" | Set-Content -LiteralPath "$setup.sha256" -Encoding ASCII
    [pscustomobject]@{Installer=$setup;Bytes=(Get-Item -LiteralPath $setup).Length;SHA256=$hash} | ConvertTo-Json
} finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
}
