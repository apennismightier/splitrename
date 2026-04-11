; SplitRename Inno Setup Script
; Open this file in Inno Setup and press F9 to compile

#define AppName      "SplitRename"
#define AppVersion   "1.6.0"
#define AppPublisher "apennismightier"
#define AppExeName   "SplitRename.exe"

[Setup]
AppId={{A3F7C2B1-9E4D-4A8F-B3C2-1D5E6F7A8B9C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/

; Default to C:\Program Files (x86)\SplitRename
; User can change this on the install screen
DefaultDirName={commonpf32}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

; Show the directory picker so user can change if they want
DisableDirPage=no

OutputDir={#SourcePath}\installer_output
OutputBaseFilename=SplitRename_Setup
SetupIconFile={#SourcePath}\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; Request admin so we can write to Program Files (x86)
PrivilegesRequired=admin

WizardStyle=modern
DisableWelcomePage=no
DisableProgramGroupPage=yes

UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourcePath}\dist\SplitRename\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\bin"

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
Type: files;          Name: "{app}\.version_cache.json"

[Code]
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then
  begin
    MsgBox('SplitRename requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
  begin
    MsgBox(
      'SplitRename installed successfully!' + #13#10 + #13#10 +
      'On first launch, click "FFmpeg Manager" to download FFmpeg automatically.',
      mbInformation, MB_OK
    );
  end;
end;
