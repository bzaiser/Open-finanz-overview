; Inno Setup Script für Finanzplan Desktop
#define MyAppName "Finanzplan Desktop"
#define MyAppVersion "0.9.0"
#define MyAppPublisher "Finanzplan"
#define MyAppExeName "FinanzplanDesktop.exe"

[Setup]
AppId={{E5848C17-B5BD-41D4-904A-F95D22F35012}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=static\img\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
OutputDir=dist_installer
OutputBaseFilename=FinanzplanDesktop_Setup
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Alle Programmdateien installieren / überschreiben:
Source: "dist\FinanzplanDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".env,data\db.sqlite3,data\ollama\*,data\ollama"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
