# Reconstruire Meloo

Configuration de référence : Windows x64, Python 3.12.10 x64, .NET SDK 9 et Inno Setup 7.1.0.
Les outils de développement ne sont pas nécessaires à l’utilisateur de l’installateur complet.

## Application Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

`requirements.txt` fixe les dépendances directes. `requirements-lock.txt` conserve l’inventaire complet
de l’environnement historique, qui inclut des paquets exclus du programme livré ; ce n’est pas une liste
des seuls composants redistribués. Les exclusions sont définies dans `build_portable.py`.

## Moteurs locaux

- LibreOffice : extraire administrativement le MSI officiel 26.8.1 x64 dans `tools/LibreOffice`.
  Le résultat attendu est `tools/LibreOffice/program/soffice.exe`.
  L’extraction administrative `msiexec /a` ne doit pas être confondue avec une installation globale.
  SHA-256 du MSI de référence : `c6298b10cfa1748bcbedad94c62ce771e240e5021bfd6d7a967cd571b04b5312`.
- FFmpeg et Pandoc sont fournis par les roues Python `imageio-ffmpeg` et `pypandoc-binary`.
- Le volet de partage Windows se reconstruit depuis son code C# :

```powershell
dotnet publish native/Share/Share.csproj -c Release -r win-x64 --self-contained true -o tools/share -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
```

Les sources et références de licences de ces composants sont recensées dans [THIRD_PARTY.md](THIRD_PARTY.md).
Les binaires Qt sont des DLL séparées ; une version compatible modifiée peut les remplacer.
La reconstruction du programme et le débogage de telles modifications ne sont pas interdits.

## Tests et paquet portable

Exécuter depuis la racine du dépôt, avec un dossier temporaire de test dédié et vide :

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$env:ZESTE_CONFIG_DIR = "$PWD\build\test-profile"
.\.venv\Scripts\python.exe -m pytest tests --ignore=tests/test_packaged.py --basetemp=build/test-temp -q --junitxml=build/validation/source.xml
.\.venv\Scripts\python.exe build_portable.py
.\.venv\Scripts\python.exe -m pytest tests/test_packaged.py --basetemp=build/packaged-temp -q --junitxml=build/validation/packaged.xml
.\.venv\Scripts\python.exe scripts/prepare_release.py
```

`build_portable.py --skip-tools` produit seulement un build de développement sans LibreOffice ni volet de partage.
Un ancien portable généré est conservé dans un dossier daté, jamais écrasé.
Les tests natifs de la zone de notification nécessitent une session Windows interactive.
Une compilation ne démontre pas à elle seule la compatibilité avec tous les PC et documents.

## Assistant d’installation

Installer ou extraire le compilateur officiel Inno Setup dans `tools/InnoSetup`, puis :

```powershell
.\build_installer.ps1
```

Résultat : `dist/Meloo-0.4.2-Setup-x64.exe` et son SHA-256. Les scripts et images de l’assistant sont dans `installer/`.
`installer/Test-Installer.ps1` vérifie installation, conversions, réinstallation et désinstallation dans un dossier
temporaire dédié. Il refuse de s’exécuter si une installation de Meloo est déjà inscrite dans Windows.
Les tests de cycle d’installation nécessitent les droits normaux d’une session utilisateur, hors bac à sable.

Les anciens rapports restent une preuve historique pour leur version seulement. Les rapports d’une publication
ne doivent pas contenir de chemins personnels ; `prepare_release.py` n’y conserve que les compteurs et noms de tests.

Les installateurs et les archives de sources tierces vont dans les assets d’une GitHub Release,
pas dans l’historique Git. Vérifier les sources correspondantes et les notices de chaque composant avant redistribution.
