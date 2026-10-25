CONSTRUIRE L'ASSISTANT WINDOWS DE MELOO

1. Construire et valider le portable avec build_portable.py et assemble_delivery.py.
2. Télécharger Inno Setup 7 x64 depuis https://jrsoftware.org/isdl.php.
   Vérifier la signature Authenticode « Pyrsys B.V. ».
   Le compilateur peut être extrait dans tools\InnoSetup avec son mode officiel
   /PORTABLE=1 /CURRENTUSER /VERYSILENT /NOICONS /DIR="chemin\tools\InnoSetup".
3. Les images BMP de l'assistant sont incluses. Pour les régénérer :
   .\.venv\Scripts\python.exe installer\make_wizard_art.py
4. Dans PowerShell Windows :
   .\build_installer.ps1

Résultat : dist\Meloo-0.4.2-Setup-x64.exe et son empreinte SHA-256.
L'installateur embarque tout le portable, ses sources, moteurs, licences et rapports.
Il ne télécharge aucun composant à l'installation.

Installation par utilisateur, Windows 10/11 64 bits, choix du dossier,
menu Démarrer et Bureau facultatifs, désinstallation native Windows.
Les dossiers non vides sans le marqueur de cet assistant sont refusés.
Aucune suppression récursive de fichiers utilisateur n'est programmée.
Le profil historique %LOCALAPPDATA%\Zeste reste extérieur à l'installation.
Le démarrage automatique n'est pas activé par l'assistant.

Pour tester sans démarrer l'application ni créer de raccourcis :
Meloo-0.4.2-Setup-x64.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /TASKS="" /DIR="chemin-de-test-vide" /LOG="installation.log"
Puis : chemin-de-test-vide\uninstall\unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="desinstallation.log"

Inno Setup : https://jrsoftware.org/ (compilateur officiel 7.1.0 utilisé).
L'exécutable Meloo et son installateur ne sont pas signés avec un certificat éditeur.
