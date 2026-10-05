#define AppName "EduPaie"
#define AppVersion "1.0.0"

[Setup]
AppId={{3F8B2D6E-7A41-4C9B-A5D2-8E6F1B0C4A97}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=EduPaieSetup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#AppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked

[Files]
Source: "dist\EduPaie.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\EduPaie.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\EduPaie.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EduPaie.exe"; Description: "Lancer EduPaie"; Flags: nowait postinstall skipifsilent