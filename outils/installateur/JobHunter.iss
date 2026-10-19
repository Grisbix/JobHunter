; JobHunter's Windows installer (Inno Setup 6). Built by construire.py:
;   ISCC /DVersion=2.9.0 /DSource=dist\JobHunter /Odist JobHunter.iss
; Per-user installation, without administrator rights. The data
; (profile, CVs, offers, tracker) live in Documents\JobHunter: neither installing,
; updating nor uninstalling touches them.

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Source
  #define Source "..\..\dist\JobHunter"
#endif

[Setup]
AppId={{6E3F2A41-7C1B-4F0E-9A3D-4B8C5D2E1F70}
AppName=JobHunter
AppVersion={#Version}
AppVerName=JobHunter {#Version}
AppPublisher=Grisbix
AppPublisherURL=https://github.com/Grisbix/JobHunter
AppSupportURL=https://github.com/Grisbix/JobHunter/issues
AppUpdatesURL=https://github.com/Grisbix/JobHunter/releases/latest
DefaultDirName={localappdata}\Programs\JobHunter
DefaultGroupName=JobHunter
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=JobHunterSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\JobHunter.exe
CloseApplications=yes

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "bureau"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; The program folder is replaced entirely: an older version leaves
; no stale module behind.
Source: "{#Source}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\JobHunter"; Filename: "{app}\JobHunter.exe"
Name: "{autodesktop}\JobHunter"; Filename: "{app}\JobHunter.exe"; Tasks: bureau

[Run]
Filename: "{app}\JobHunter.exe"; Description: "{cm:LaunchProgram,JobHunter}"; Flags: nowait postinstall skipifsilent
