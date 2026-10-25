; Build with build_installer.ps1. The payload is the validated portable release.
#ifndef AppVersion
  #define AppVersion "0.4.2"
#endif
#ifndef PayloadDir
  #define PayloadDir SourcePath + "..\dist\Zeste"
#endif
#ifndef OutputFolder
  #define OutputFolder SourcePath + "..\dist"
#endif
#ifndef AppIdValue
  #define AppIdValue "{{F04D945E-FC72-4D36-8C23-C455AE49367B}"
#endif

[Setup]
AppId={#AppIdValue}
AppName=Meloo
AppVersion={#AppVersion}
AppVerName=Meloo {#AppVersion}
AppPublisher=Meloo
VersionInfoVersion={#AppVersion}.0
VersionInfoDescription=Assistant d'installation de Meloo
DefaultDirName={localappdata}\Programs\Meloo
DefaultGroupName=Meloo
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupArchitecture=x64
MinVersion=10.0
WizardStyle=modern dynamic
WizardSizePercent=110
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
AllowNoIcons=yes
DisableReadyPage=no
LicenseFile=..\LICENSE.txt
InfoBeforeFile=Avant-installation.txt
SetupIconFile=..\assets\zeste.ico
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
WizardImageFileDynamicDark=wizard-large.bmp
WizardSmallImageFileDynamicDark=wizard-small.bmp
OutputDir={#OutputFolder}
OutputBaseFilename=Meloo-{#AppVersion}-Setup-x64
Compression=lzma2/max
LZMANumBlockThreads=2
SolidCompression=yes
DiskSpanning=no
UninstallDisplayName=Meloo {#AppVersion}
UninstallDisplayIcon={app}\Meloo.exe
UninstallFilesDir={app}\uninstall
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Messages]
WelcomeLabel1=Bienvenue dans l'assistant d'installation de Meloo
WelcomeLabel2=Meloo convertit, compresse et organise vos fichiers sur votre PC.%n%nCet assistant installe la version {#AppVersion} et ses moteurs de conversion. Aucun téléchargement supplémentaire n'est nécessaire.
FinishedLabel=Meloo est installé.%n%nL'application démarre dans la zone de notification, près de l'horloge. Glissez un fichier depuis l'Explorateur, appuyez sur Ctrl puis déposez-le sur la roue.%n%nLes thèmes Orange et Melina sont disponibles dans Réglages.

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "__pycache__\*,*.pyc,*.pdb,*.dmp,*.log,.~lock.*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "Utiliser-Meloo.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "Meloo.iss"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "Avant-installation.txt"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "Utiliser-Meloo.txt"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "wizard-*.bmp"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "make_wizard_art.py"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "..\build_installer.ps1"; DestDir: "{app}\source"; Flags: ignoreversion
Source: "install-marker.ini"; DestDir: "{app}"; DestName: ".meloo-setup.ini"; Flags: ignoreversion
Source: "install-marker.ini"; DestDir: "{app}\source\installer"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}\source\installer"; Flags: ignoreversion

[Icons]
Name: "{group}\Meloo"; Filename: "{app}\Meloo.exe"; WorkingDir: "{app}"
Name: "{group}\Guide de Meloo"; Filename: "{app}\Utiliser-Meloo.txt"
Name: "{autodesktop}\Meloo"; Filename: "{app}\Meloo.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Meloo.exe"; Description: "Lancer Meloo dans la zone de notification"; Flags: nowait postinstall skipifsilent

[Code]
// Never install over an unrelated folder, including the old portable release.
function DestinationError: String;
var
  Directory, Product: String;
  Found: TFindRec;
  HasContent: Boolean;
begin
  Result := '';
  Directory := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if (Length(Directory) < 4) or
     (CompareText(Directory, GetEnv('USERPROFILE')) = 0) or
     (CompareText(Directory, ExpandConstant('{localappdata}')) = 0) or
     (CompareText(Directory, ExpandConstant('{autodesktop}')) = 0) or
     (CompareText(Directory, ExpandConstant('{userdocs}')) = 0) then
  begin
    Result := 'Choisissez un dossier dédié à Meloo, par exemple ' +
      ExpandConstant('{localappdata}\Programs\Meloo') + '.';
    Exit;
  end;
  Product := GetIniString('Setup', 'Product', '', Directory + '\.meloo-setup.ini');
  if Product = 'Meloo-F04D945E-FC72-4D36-8C23-C455AE49367B' then Exit;
  HasContent := False;
  if FindFirst(Directory + '\*', Found) then
  begin
    try
      repeat
        if (Found.Name <> '.') and (Found.Name <> '..') then
          HasContent := True;
      until not FindNext(Found);
    finally
      FindClose(Found);
    end;
  end;
  if HasContent then
    Result := 'Ce dossier contient déjà des fichiers. Choisissez un dossier vide ' +
      'ou une installation créée par cet assistant. Votre ancienne version portable peut être conservée séparément.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorText: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    ErrorText := DestinationError;
    if ErrorText <> '' then
    begin
      SuppressibleMsgBox(ErrorText, mbError, MB_OK, IDOK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // Revalidate immediately before extraction, including silent installs.
  Result := DestinationError;
end;
