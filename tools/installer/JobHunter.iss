; JobHunter's Windows installer (Inno Setup 6). Built by build.py:
;   ISCC /DVersion=2.9.0 /DSource=dist\JobHunter /Odist JobHunter.iss
; Per-user installation, without administrator rights. The data
; (profile, CVs, offers, tracker) live in Documents\JobHunter: neither installing nor
; updating touches them; uninstalling asks, « No » by default, and sends them to the
; Recycle Bin on « Yes » ([Code] below).

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
; JobHunter's icon on JobHunterSetup.exe and its pages, not Inno Setup's.
SetupIconFile=..\..\src\jobhunter\app\assets\jobhunter.ico
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
; The windows' identity: pinned, the taskbar keeps the shortcut's icon and entry.
Name: "{autoprograms}\JobHunter"; Filename: "{app}\JobHunter.exe"; AppUserModelID: "Grisbix.JobHunter"
Name: "{autodesktop}\JobHunter"; Filename: "{app}\JobHunter.exe"; Tasks: bureau; AppUserModelID: "Grisbix.JobHunter"

[Run]
Filename: "{app}\JobHunter.exe"; Description: "{cm:LaunchProgram,JobHunter}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
fr.EffacerDonnees=Supprimer aussi vos données JobHunter (profil, CV, lettres, offres, candidatures suivies) ?%n%n%1%n%nOui : elles partent à la Corbeille, d'où on peut les restaurer tant qu'elle n'est pas vidée.%nNon : elles restent pour une prochaine installation.
en.EffacerDonnees=Also remove your JobHunter data (profile, CVs, letters, offers, tracked applications)?%n%n%1%n%nYes: it goes to the Recycle Bin, where it can be restored until it is emptied.%nNo: it stays for a later installation.

[Code]
// The user, 2026-10-29: uninstalling kept everything without saying so. The data is the
// least replaceable thing (an application sent cannot be found again): « No » by
// default, the Recycle Bin rather than a deletion, nothing asked in a silent uninstall.

function PowerShell(const Script: String): Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "' + Script + '"', '', SW_HIDE,
    ewWaitUntilTerminated, Code) and (Code = 0);
end;

// A PowerShell single-quoted string: the only character to double is the quote.
function Litteral(const S: String): String;
begin
  Result := S;
  StringChangeEx(Result, '''', '''''', True);
  Result := '''' + Result + '''';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Donnees: String;
begin
  if CurUninstallStep = usUninstall then
    // The daily collection runs this installation's jobhunter-cli.exe: without it, the
    // task would fail every morning. A task of another installation is left alone.
    PowerShell('$t = Get-ScheduledTask -TaskName ''JobHunter - collecte quotidienne'' -ErrorAction SilentlyContinue; '
      + 'if ($t -and ($t.Actions[0].Execute.Trim([char]34) -like (' + Litteral(ExpandConstant('{app}')) + ' + ''\*''))) '
      + '{ Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false }');
  if CurUninstallStep = usPostUninstall then
  begin
    Donnees := ExpandConstant('{userdocs}\JobHunter');
    if UninstallSilent or not DirExists(Donnees) then
      Exit;
    if MsgBox(FmtMessage(CustomMessage('EffacerDonnees'), [Donnees]), mbConfirmation,
      MB_YESNO or MB_DEFBUTTON2) = IDYES then
      PowerShell('Add-Type -AssemblyName Microsoft.VisualBasic; '
        + '[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(' + Litteral(Donnees)
        + ', ''OnlyErrorDialogs'', ''SendToRecycleBin'')');
  end;
end;
