#ifndef RepoRoot
  #define RepoRoot "..\.."
#endif
#define AppVersion "0.1.0"

[Setup]
AppId={{30BC14C4-482C-44EC-A81D-9E6F6989561A}
AppName=Протокол разногласий
AppVersion={#AppVersion}
AppPublisher=Disagreement Protocol
DefaultDirName={localappdata}\Programs\DisagreementProtocol
DefaultGroupName=Протокол разногласий
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#RepoRoot}\dist\windows
OutputBaseFilename=DisagreementProtocol-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\DisagreementProtocol.exe
AppMutex=Local\DisagreementProtocol.Desktop
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked

[Files]
Source: "{#RepoRoot}\dist\windows\DisagreementProtocol\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Протокол разногласий"; Filename: "{app}\DisagreementProtocol.exe"
Name: "{autodesktop}\Протокол разногласий"; Filename: "{app}\DisagreementProtocol.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DisagreementProtocol.exe"; Description: "Запустить приложение"; Flags: nowait postinstall skipifsilent

; User documents in {localappdata}\DisagreementProtocol are deliberately retained.
