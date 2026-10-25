# Installation facultative par utilisateur, sans administrateur ni telechargement.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Destination = (Join-Path $env:LOCALAPPDATA 'Programs\Meloo'),
    [switch]$DesktopShortcut,
    [switch]$NoShortcuts
)
$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $source 'Meloo.exe') -PathType Leaf)) {
    $source = Join-Path $PSScriptRoot 'dist\Zeste'
}
$source = (Resolve-Path -LiteralPath $source).Path
if (-not (Test-Path -LiteralPath (Join-Path $source 'Meloo.exe') -PathType Leaf)) {
    throw 'Meloo.exe introuvable. Conserver ce script a cote du portable complet.'
}
$sourceManifest = Join-Path $source '.zeste-generated.json'
if (-not (Test-Path -LiteralPath $sourceManifest -PathType Leaf)) { throw 'Portable non identifie : installation interrompue.' }
$manifest = Get-Content -LiteralPath $sourceManifest -Raw | ConvertFrom-Json
if ($manifest.product -ne 'zeste-windows-portable') { throw 'Ce dossier ne contient pas une distribution Meloo reconnue.' }
$destinationPath = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
if ($destinationPath -eq [IO.Path]::GetPathRoot($destinationPath).TrimEnd('\')) { throw 'Choisir un sous-dossier pour Meloo.' }
if ($destinationPath.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase) -or $destinationPath -eq $source) {
    throw 'La destination ne doit pas se trouver dans le portable source.'
}
if (Test-Path -LiteralPath $destinationPath) {
    $item = Get-Item -LiteralPath $destinationPath
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Une jonction ou un lien ne peut pas servir de destination.' }
    if (Get-ChildItem -LiteralPath $destinationPath -Force | Select-Object -First 1) {
        $installedManifest = Join-Path $destinationPath '.zeste-install.json'
        if (-not (Test-Path -LiteralPath $installedManifest -PathType Leaf)) {
            throw 'Destination deja occupee par des fichiers non identifies. Choisir un dossier vide.'
        }
        $installed = Get-Content -LiteralPath $installedManifest -Raw | ConvertFrom-Json
        if ($installed.product -ne 'zeste-windows') { throw 'Destination non reconnue : fichiers existants conserves.' }
    }
}
$versionName = '0.4.2-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$versionPath = [IO.Path]::GetFullPath((Join-Path $destinationPath ('versions\' + $versionName)))
if (-not $versionPath.StartsWith($destinationPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Chemin de version invalide.' }
if (Test-Path -LiteralPath $versionPath) { throw 'Cette version existe deja : aucun fichier ne sera remplace.' }
if (-not $PSCmdlet.ShouldProcess($versionPath, 'Copier le portable Meloo et creer les raccourcis')) { return }
New-Item -ItemType Directory -Path $versionPath -Force | Out-Null
Get-ChildItem -LiteralPath $source -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $versionPath -Recurse -Force
}
$exePath = Join-Path $versionPath 'Meloo.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw 'La copie de Meloo a echoue.' }
@{ product = 'zeste-windows'; version = '0.4.2'; current = $versionPath; installedAt = (Get-Date -Format o) } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $destinationPath '.zeste-install.json') -Encoding UTF8
if (-not $NoShortcuts) {
    $shell = New-Object -ComObject WScript.Shell
    $locations = @([Environment]::GetFolderPath('Programs'))
    if ($DesktopShortcut) { $locations += [Environment]::GetFolderPath('DesktopDirectory') }
    foreach ($location in $locations) {
        $linkPath = Join-Path $location 'Meloo.lnk'
        if (Test-Path -LiteralPath $linkPath) {
            $existing = $shell.CreateShortcut($linkPath)
            if (-not $existing.TargetPath.StartsWith($destinationPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
                Write-Warning "Raccourci existant conserve : $linkPath"
                continue
            }
        }
        $shortcut = $shell.CreateShortcut($linkPath)
        $shortcut.TargetPath = $exePath
        $shortcut.WorkingDirectory = $versionPath
        $shortcut.IconLocation = $exePath + ',0'
        $shortcut.Description = 'Meloo - convertisseur local de fichiers'
        $shortcut.Save()
    }
}
Write-Host "Meloo 0.4.2 installe : $exePath"
Write-Host 'Les versions precedentes sont conservees. Les preferences restent dans votre profil existant (Zeste).'
