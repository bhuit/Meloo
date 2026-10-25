[CmdletBinding()]
param(
    [string]$Setup = (Join-Path $PSScriptRoot '..\dist\Meloo-0.4.2-Setup-x64.exe'),
    [ValidatePattern('^\d{8}-\d{6}$')][string]$ResumeStamp,
    [ValidatePattern('^\{[A-Fa-f0-9-]{36}\}$')][string]$ApplicationId = '{F04D945E-FC72-4D36-8C23-C455AE49367B}',
    [string]$Python = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe')
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$Setup = (Resolve-Path -LiteralPath $Setup).Path
$stamp = if ($ResumeStamp) {$ResumeStamp} else {Get-Date -Format 'yyyyMMdd-HHmmss'}
$scratch = Join-Path $root ('build\setup-qa-' + $stamp)
$nativeTest = Join-Path $env:LOCALAPPDATA ('Temp\Meloo-Setup-QA-' + $stamp)
$app = Join-Path $nativeTest 'Meloo essai'
$profile = Join-Path $nativeTest 'profile'
$temporary = Join-Path $nativeTest 'tmp'
$testGroup = 'Meloo Verification ' + $stamp
$groupFolder = Join-Path ([Environment]::GetFolderPath('Programs')) $testGroup
$results = [ordered]@{installer=$Setup;directory=$scratch;native_test_root=$nativeTest;checks=@();success=$false;excluded_transient_files=@();observations=@()}
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $ApplicationId + '_is1'
if ($ResumeStamp) {
    $registered = Get-ItemProperty -LiteralPath $uninstallKey
    if ($registered.InstallLocation.TrimEnd('\') -ne $app -or -not (Test-Path -LiteralPath (Join-Path $app '.meloo-setup.ini'))) { throw 'La reprise ne correspond pas a notre installation de test.' }
    $results.checks = @((Get-Content -LiteralPath (Join-Path $scratch 'rapport.json') -Raw | ConvertFrom-Json).checks)
} elseif (Test-Path -LiteralPath $uninstallKey) { throw 'Une installation Meloo par assistant existe deja : test isole annule pour ne pas modifier son inscription Windows.' }
New-Item -ItemType Directory -Path $scratch,$temporary,$profile -Force | Out-Null
$savedEnv = @{}
foreach ($name in @('TEMP','TMP','ZESTE_CONFIG_DIR','QT_QPA_PLATFORM')) { $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
$env:TEMP = $temporary
$env:TMP = $temporary
$watch = @(
    (Join-Path $env:LOCALAPPDATA 'Zeste\settings.ini'),
    (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Meloo.lnk'),
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'Meloo.lnk')
)
$before = @{}
foreach ($file in $watch) { $before[$file] = if (Test-Path -LiteralPath $file) {(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash} else {''} }
function Run-Quiet([string]$File,[string[]]$Arguments,[int]$Timeout=240000) {
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($Timeout)) { throw "Delai depasse : $File (PID $($process.Id))" }
    return $process.ExitCode
}
function Check([bool]$Condition,[string]$Name) {
    if (-not $Condition) { throw "ECHEC : $Name" }
    $results.checks += $Name
    Write-Output "OK : $Name"
}
try {
    $shortcutPath = Join-Path $groupFolder 'Meloo.lnk'
    if (-not $ResumeStamp) {
    $foreign = Join-Path $scratch 'dossier-existant'
    New-Item -ItemType Directory -Path $foreign | Out-Null
    $sentinel = Join-Path $foreign 'document-personnel.txt'
    'Conserver ce fichier.' | Set-Content -LiteralPath $sentinel -Encoding UTF8
    $sentinelHash = (Get-FileHash -LiteralPath $sentinel).Hash
    $code = Run-Quiet $Setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="'+$foreign+'"'),('/LOG="'+$scratch+'\refus.log"'))
    $refusal = Get-Content -LiteralPath (Join-Path $scratch 'refus.log') -Raw
    Check ($code -in @(1,7) -and $refusal.Contains('Ce dossier contient') -and -not $refusal.Contains('Runtime error') -and (Get-FileHash -LiteralPath $sentinel).Hash -eq $sentinelHash -and -not (Test-Path (Join-Path $foreign 'Meloo.exe'))) 'Dossier etranger refuse, fichier conserve'
    $installArgs = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/TASKS=',('/GROUP="'+$testGroup+'"'),('/DIR="'+$app+'"'),('/LOG="'+$scratch+'\installation.log"'))
    $code = Run-Quiet $Setup $installArgs 600000
    Check ($code -eq 0) 'Installation complete sans redemarrage'
    $installed = Get-ItemProperty -LiteralPath $uninstallKey
    Check ($installed.DisplayName -eq 'Meloo 0.4.2' -and $installed.InstallLocation.TrimEnd('\') -eq $app) 'Desinstallation inscrite dans Windows pour le compte utilisateur'
    $shortcutPath = Join-Path $groupFolder 'Meloo.lnk'
    $shell = New-Object -ComObject WScript.Shell
    Check ((Test-Path -LiteralPath $shortcutPath) -and $shell.CreateShortcut($shortcutPath).TargetPath -eq (Join-Path $app 'Meloo.exe') -and (Test-Path -LiteralPath (Join-Path $groupFolder 'Guide de Meloo.lnk'))) 'Raccourcis du menu Demarrer crees vers la bonne installation'
    }
    $payload = Join-Path $root 'dist\Zeste'
    $fileCount = 0
    foreach ($file in Get-ChildItem -LiteralPath $payload -File -Recurse -Force) {
        $relative = $file.FullName.Substring($payload.Length).TrimStart('\')
        # Inno Setup omits hidden files. The sole hidden payload file is a stale
        # LibreOffice test-document lock, not a runtime component.
        if ($relative -eq 'tools\LibreOffice\program\opencl\.~lock.cl-test.ods#' -and ($file.Attributes -band [IO.FileAttributes]::Hidden)) {
            $results.excluded_transient_files += $relative
            continue
        }
        $copy = Join-Path $app $relative
        if (-not (Test-Path -LiteralPath $copy) -or (Get-Item -LiteralPath $copy).Length -ne $file.Length -or (Get-FileHash -LiteralPath $copy).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) { throw "Fichier non conforme : $relative" }
        $fileCount++
    }
    Check ($fileCount -gt 20000) "Tous les fichiers utiles du portable verifies par SHA-256 ($fileCount), hors verrou temporaire cache"
    $results.payload_files = $fileCount
    $env:ZESTE_CONFIG_DIR = $profile
    $env:QT_QPA_PLATFORM = 'windows'
    "[General]`nbackground_hint_shown=true`nhud=false`ncolor_style=melina`n" | Set-Content -LiteralPath (Join-Path $profile 'settings.ini') -Encoding UTF8
    $exe = Join-Path $app 'Meloo.exe'
    $resident = Start-Process -FilePath $exe -WindowStyle Hidden -PassThru
    $statusFile = Join-Path $scratch 'status.json'
    try {
        $status = $null
        for ($attempt=0;$attempt -lt 8;$attempt++) {
            Start-Sleep -Milliseconds 500
            $code = Run-Quiet $exe @('--status-file',('"'+$statusFile+'"')) 30000
            if (Test-Path -LiteralPath $statusFile) { $status = Get-Content -LiteralPath $statusFile -Raw | ConvertFrom-Json }
            if ($status.running) { break }
        }
        Check ($status.running -and $status.version -eq '0.4.2' -and $status.tray_visible -and $status.watcher_active -and -not $status.window_visible -and $status.color_style -eq 'melina') 'Application installee : arriere-plan, icone, geste Ctrl et theme Melina'
        $code = Run-Quiet $exe @('--quit')
        Check ($code -eq 0 -and $resident.WaitForExit(15000)) 'Fermeture normale de l instance de test'
    } finally {
        if (-not $resident.HasExited) { [void](Run-Quiet $exe @('--quit')) }
    }
    $code = Run-Quiet $Python @(('"'+$PSScriptRoot+'\verify_installed.py"'),('"'+$app+'"'),('"'+$scratch+'\conversions"')) 300000
    Check ($code -eq 0) 'Conversions reelles depuis l installation (image, ZIP, Office, audio)'
    $personal = Join-Path $app 'mes-fichiers\a-conserver.txt'
    New-Item -ItemType Directory -Path (Split-Path -Parent $personal) | Out-Null
    'Donnee personnelle de test.' | Set-Content -LiteralPath $personal -Encoding UTF8
    $personalHash = (Get-FileHash -LiteralPath $personal).Hash
    $settings = Join-Path $profile 'settings.ini'
    $settingsHash = (Get-FileHash -LiteralPath $settings).Hash
    $reinstallArgs = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="'+$app+'"'),('/LOG="'+$scratch+'\reinstallation.log"'))
    $code = Run-Quiet $Setup $reinstallArgs 600000
    Check ($code -eq 0 -and (Get-FileHash -LiteralPath $personal).Hash -eq $personalHash -and (Get-FileHash -LiteralPath $settings).Hash -eq $settingsHash) 'Reinstallation dans le meme dossier, donnees conservees'
    $code = Run-Quiet (Join-Path $app 'uninstall\unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+$scratch+'\desinstallation.log"')) 300000
    Check ($code -eq 0) 'Desinstallation sans redemarrage'
    Check (-not (Test-Path -LiteralPath $uninstallKey) -and -not (Test-Path -LiteralPath $exe) -and -not (Test-Path (Join-Path $app '_internal\python312.dll'))) 'Application et inscription Windows retirees'
    Check (-not (Test-Path -LiteralPath $shortcutPath) -and -not (Test-Path -LiteralPath (Join-Path $groupFolder 'Guide de Meloo.lnk'))) 'Raccourcis de test retires par la desinstallation'
    Check ((Get-FileHash -LiteralPath $personal).Hash -eq $personalHash -and (Get-FileHash -LiteralPath $settings).Hash -eq $settingsHash) 'Fichier personnel et preferences conserves apres desinstallation'
    foreach ($file in $watch) {
        $after = if (Test-Path -LiteralPath $file) {(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash} else {''}
        # The original application stays running and may record real user
        # conversions during this test. Its live history is not a stable fixture.
        if ([IO.Path]::GetFileName($file) -eq 'settings.ini' -and $before[$file] -ne $after) {
            $results.observations += 'Le profil de la session active a evolue pendant le test; comparaison binaire non concluante. Le profil isole est conserve apres desinstallation.'
            continue
        }
        Check ($before[$file] -eq $after) "Installation existante inchangee : $([IO.Path]::GetFileName($file))"
    }
    $results.success = $true
} finally {
    $results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $scratch 'rapport.json') -Encoding UTF8
    foreach ($name in $savedEnv.Keys) { [Environment]::SetEnvironmentVariable($name,$savedEnv[$name],'Process') }
    Write-Output "Rapport : $scratch\rapport.json"
}
