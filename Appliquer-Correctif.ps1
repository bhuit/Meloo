param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][string]$InstallRoot,
    [Parameter(Mandatory=$true)][string]$ExpectedHash,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$installDirectory = (Resolve-Path -LiteralPath $InstallRoot).Path.TrimEnd('\')
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
if ((Get-Item -LiteralPath $installDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Installation liée non prise en charge.' }
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $ExpectedHash) { throw 'Empreinte ZIP incorrecte.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipReader = [IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    $entry = $zipReader.GetEntry('Zeste/validation/patch-0.4.1.json')
    if (-not $entry) { throw 'Manifeste du correctif absent.' }
    $reader = [IO.StreamReader]::new($entry.Open())
    try { $patch = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
    foreach ($item in $zipReader.Entries) {
        if (-not $item.FullName.StartsWith('Zeste/') -or $item.FullName.Contains('..') -or $item.FullName.Contains(':')) { throw 'Chemin ZIP non autorisé.' }
    }
} finally { $zipReader.Dispose() }
$markerPath = Join-Path $installDirectory '.zeste-generated.json'
$marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
if ($marker.product -ne 'zeste-windows-portable' -or $marker.version -ne $patch.base_version) { throw 'Ce correctif exige Meloo 0.4.0.' }
$executable = Join-Path $installDirectory 'Meloo.exe'
if ((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash -ne $patch.base_executable_sha256) { throw 'Exécutable de base différent ; installation conservée.' }
$files = @($patch.files_sha256.PSObject.Properties.Name) + 'validation/patch-0.4.1.json'
function Get-CheckedTarget([string]$relative) {
    $target = [IO.Path]::GetFullPath((Join-Path $installDirectory $relative))
    if (-not $target.StartsWith($installDirectory + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination hors installation.' }
    $directory = Split-Path -Parent $target
    while ($directory.Length -ge $installDirectory.Length) {
        if ((Test-Path -LiteralPath $directory) -and ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Destination liée non prise en charge.' }
        if ($directory -eq $installDirectory) { break }
        $directory = Split-Path -Parent $directory
    }
    return $target
}
foreach ($relative in $files) { $null = Get-CheckedTarget $relative }
if (-not $Apply) {
    [pscustomobject]@{Mode='Verification';Installation=$installDirectory;Version=$patch.version;Files=$files.Count;ArchiveHash=$ExpectedHash} | ConvertTo-Json
    return
}
$backupDirectory = Join-Path (Split-Path -Parent $installDirectory) ('Sauvegarde-Meloo-0.4.0-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $backupDirectory) { throw 'Le dossier de sauvegarde existe déjà.' }
$null = New-Item -ItemType Directory -Path $backupDirectory
$stagingDirectory = Join-Path $backupDirectory 'correctif-verifie'
Expand-Archive -LiteralPath $archivePath -DestinationPath $stagingDirectory
foreach ($item in $patch.files_sha256.PSObject.Properties) {
    $staged = Join-Path (Join-Path $stagingDirectory 'Zeste') $item.Name
    if ((Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash -ne $item.Value) { throw ('Contenu incorrect : ' + $item.Name) }
}
$quitter = Start-Process -FilePath $executable -ArgumentList '--quit' -WindowStyle Hidden -PassThru
if (-not $quitter.WaitForExit(15000)) { throw 'Zeste ne répond pas à la demande de fermeture.' }
$deadline = (Get-Date).AddSeconds(15)
do {
    $running = @(Get-Process -Name Zeste,Meloo -ErrorAction SilentlyContinue | Where-Object { $_.Path -in @($executable,(Join-Path $installDirectory 'Zeste.exe')) })
    if (-not $running) { break }
    Start-Sleep -Milliseconds 200
} while ((Get-Date) -lt $deadline)
if ($running) { throw 'Zeste traite encore un fichier ; installation conservée.' }
$replaced = [Collections.Generic.List[string]]::new()
$created = [Collections.Generic.List[string]]::new()
try {
    foreach ($relative in $files) {
        $target = Get-CheckedTarget $relative
        $backup = Join-Path (Join-Path $backupDirectory 'ancienne-version') $relative
        if (Test-Path -LiteralPath $target) {
            $null = New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force
            Copy-Item -LiteralPath $target -Destination $backup
            $replaced.Add($relative)
        } else { $created.Add($relative) }
        $null = New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force
        Copy-Item -LiteralPath (Join-Path (Join-Path $stagingDirectory 'Zeste') $relative) -Destination $target -Force
    }
    foreach ($item in $patch.files_sha256.PSObject.Properties) {
        if ((Get-FileHash -LiteralPath (Get-CheckedTarget $item.Name) -Algorithm SHA256).Hash -ne $item.Value) { throw 'Échec de vérification après copie.' }
    }
} catch {
    foreach ($relative in $replaced) { Copy-Item -LiteralPath (Join-Path (Join-Path $backupDirectory 'ancienne-version') $relative) -Destination (Get-CheckedTarget $relative) -Force }
    foreach ($relative in $created) { $target = Get-CheckedTarget $relative; if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target } }
    throw
}
$executable = Join-Path $installDirectory 'Meloo.exe'
Start-Process -FilePath $executable -WorkingDirectory $installDirectory -WindowStyle Hidden
$statusPath = Join-Path $backupDirectory 'etat-apres-mise-a-jour.json'
$status = $null
for ($attempt = 0; $attempt -lt 4; $attempt++) {
    $statusProcess = Start-Process -FilePath $executable -ArgumentList @('--status-file',('"' + $statusPath + '"')) -WindowStyle Hidden -PassThru
    if (-not $statusProcess.WaitForExit(15000)) { throw 'Mise à jour copiée ; diagnostic de lancement indisponible.' }
    $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    if ($status.running -and $status.version -eq $patch.version) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $status.running -or $status.version -ne $patch.version) { throw 'Mise à jour copiée ; le lancement reste à vérifier.' }
[pscustomobject]@{Mode='Applique';Installation=$installDirectory;Backup=$backupDirectory;Status=$status} | ConvertTo-Json -Depth 5
