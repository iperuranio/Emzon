; Windows installer: iscc /DAppVersion=X.Y.Z packaging\emzon.iss
; Installs for the current user by default, so no administrator rights are needed.

#ifndef AppVersion
  #error AppVersion must be defined
#endif

#define AppName "Emzon"
#define AppExe "Emzon.exe"
#define AppId "dev.metessi.emzon"
#define AppGuid "6E1F4A2B-8C3D-4E5F-9A7B-2C1D0E9F8A6B"

[Setup]
AppId={{{#AppGuid}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Metessi
AppPublisherURL=https://github.com/iperuranio/Emzon
DefaultDirName={autopf}\{#AppName}
DefaultGroupName=Metessi
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=Emzon-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=auto
DisableReadyPage=no
CloseApplications=yes
ChangesAssociations=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Emzon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Metessi\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "{#AppId}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; AppUserModelID: "{#AppId}"; Tasks: desktopicon

[Registry]
; "Open with" entry for videos, without becoming the default player.
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".mp4"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".mkv"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".mov"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".m4v"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".webm"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".avi"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\.mp4\OpenWithList\{#AppExe}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.mkv\OpenWithList\{#AppExe}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.mov\OpenWithList\{#AppExe}"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
italian.UpdateTitle=Aggiornamento di Emzon
italian.UpdateText=Sul computer c’è Emzon %1. Questa procedura lo aggiorna alla versione %2.%n%nImpostazioni ed export restano dove sono. Se Emzon è aperto viene chiuso, e alla fine puoi riaprirlo da qui.
italian.SameTitle=Emzon %1 è già installato
italian.SameText=Puoi reinstallarlo: impostazioni ed export restano dove sono.
italian.OlderTitle=Sul computer c’è una versione più recente
italian.OlderText=È installato Emzon %1, più recente di questa versione (%2). Continuando, torni alla %2.
italian.UpdateButton=Aggiorna
italian.UpdateDone=Emzon è aggiornato alla versione %1.
english.UpdateTitle=Updating Emzon
english.UpdateText=Emzon %1 is installed on this computer. This will update it to version %2.%n%nSettings and exports stay where they are. If Emzon is open it will be closed, and you can reopen it at the end.
english.SameTitle=Emzon %1 is already installed
english.SameText=You can reinstall it: settings and exports stay where they are.
english.OlderTitle=A newer version is installed
english.OlderText=Emzon %1 is installed, newer than this version (%2). Continuing goes back to %2.
english.UpdateButton=Update
english.UpdateDone=Emzon has been updated to version %1.

[Code]
var
  Installed: String;

function InstalledVersion(): String;
begin
  Result := '';
  RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#AppGuid}}_is1', 'DisplayVersion', Result);
end;

// Numeric comparison of MAJOR.MINOR.PATCH, so 0.10.0 is newer than 0.9.0.
function CompareVersions(A, B: String): Integer;
var
  PartA, PartB, DotA, DotB: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    DotA := Pos('.', A);
    DotB := Pos('.', B);
    if DotA = 0 then DotA := Length(A) + 1;
    if DotB = 0 then DotB := Length(B) + 1;
    PartA := StrToIntDef(Copy(A, 1, DotA - 1), 0);
    PartB := StrToIntDef(Copy(B, 1, DotB - 1), 0);
    if PartA > PartB then Result := 1
    else if PartA < PartB then Result := -1;
    Delete(A, 1, DotA);
    Delete(B, 1, DotB);
  end;
end;

function InitializeSetup(): Boolean;
begin
  Installed := InstalledVersion();
  if Installed = '' then
    Log('Emzon: fresh install of {#AppVersion}')
  else
    Log('Emzon: updating from ' + Installed + ' to {#AppVersion}');
  Result := True;
end;

procedure InitializeWizard();
var
  Order: Integer;
begin
  if Installed = '' then
    Exit;
  Order := CompareVersions(Installed, '{#AppVersion}');
  if Installed = '{#AppVersion}' then
  begin
    WizardForm.WelcomeLabel1.Caption := FmtMessage(CustomMessage('SameTitle'), [Installed]);
    WizardForm.WelcomeLabel2.Caption := CustomMessage('SameText');
  end
  else if Order > 0 then
  begin
    WizardForm.WelcomeLabel1.Caption := CustomMessage('OlderTitle');
    WizardForm.WelcomeLabel2.Caption := FmtMessage(CustomMessage('OlderText'), [Installed, '{#AppVersion}']);
  end
  else
  begin
    WizardForm.WelcomeLabel1.Caption := CustomMessage('UpdateTitle');
    WizardForm.WelcomeLabel2.Caption := FmtMessage(CustomMessage('UpdateText'), [Installed, '{#AppVersion}']);
    WizardForm.Caption := CustomMessage('UpdateTitle');
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (Installed <> '') and (Installed <> '{#AppVersion}') then
  begin
    if CurPageID = wpReady then
      WizardForm.NextButton.Caption := CustomMessage('UpdateButton');
    if CurPageID = wpFinished then
      WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('UpdateDone'), ['{#AppVersion}']);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
  App: String;
begin
  Result := '';
  App := ExpandConstant('{app}\{#AppExe}');
  // Ask an open Emzon to close itself cleanly; one that is exporting stays open
  // and the setup's own check for files in use takes over.
  if FileExists(App) then
    Exec(App, '--quit', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Sleep(1500);
end;
