#ifndef AppVersion
  #define AppVersion "0.1.10"
#endif
#ifndef AppSource
  #define AppSource "..\..\target\release"
#endif

[Setup]
AppId={{9F2435CA-0DE7-4553-957A-AE8F250E93C5}
AppName=GoreeCloud Rich Text Editor
AppVersion={#AppVersion}
AppPublisher=GoreeCloud Rich Text Editor
AppPublisherURL=https://github.com/GoreeCloud/rich-text-editor
DefaultDirName={localappdata}\Programs\goreecloud-rich-text-editor
DisableDirPage=no
DisableProgramGroupPage=yes
DisableWelcomePage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\..\dist\windows
OutputBaseFilename=goreecloud-rich-text-editor-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\assets\branding\app-icon.ico
UninstallDisplayIcon={app}\goreecloud_rich_text_editor.exe
WizardStyle=modern light
WizardSmallImageFile=wizard-logo.bmp
WizardSmallImageBackColor=$FFFFFF
WizardImageStretch=no
WizardSizePercent=105,105
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes
SetupLogging=yes
#ifdef Signed
SignTool=goreecloudrte
SignedUninstaller=yes
SignedUninstallerDir={#AppSource}
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SelectDirLabel3=Choose an install folder. Your notes are stored separately.
SelectTasksLabel2=Make GoreeCloud Rich Text Editor easier to reach.
FinishedLabel=GoreeCloud Rich Text Editor is ready. A quiet place for your notes.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#AppSource}\goreecloud_rich_text_editor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppSource}\vcruntime140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"
Source: "..\..\THIRD_PARTY.md"; DestDir: "{app}"

[Icons]
Name: "{userprograms}\GoreeCloud Rich Text Editor"; Filename: "{app}\goreecloud_rich_text_editor.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\GoreeCloud Rich Text Editor"; Filename: "{app}\goreecloud_rich_text_editor.exe"; WorkingDir: "{app}"; Tasks: desktopicon

; "Open with" for Markdown files (not the default app): they are edited in place.
[Registry]
Root: HKA; Subkey: "Software\Classes\GoreeCloudRte.Markdown"; ValueType: string; ValueName: ""; ValueData: "Markdown"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\GoreeCloudRte.Markdown\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\goreecloud_rich_text_editor.exe,0"
Root: HKA; Subkey: "Software\Classes\GoreeCloudRte.Markdown\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\goreecloud_rich_text_editor.exe"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "GoreeCloudRte.Markdown"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "GoreeCloudRte.Markdown"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Applications\goreecloud_rich_text_editor.exe\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\goreecloud_rich_text_editor.exe\SupportedTypes"; ValueType: string; ValueName: ".markdown"; ValueData: ""

[Run]
Filename: "{app}\goreecloud_rich_text_editor.exe"; Description: "Launch GoreeCloud Rich Text Editor"; Flags: nowait postinstall skipifsilent
; The in-app updater installs silently with /UPDATE=1 and expects the app back afterwards.
Filename: "{app}\goreecloud_rich_text_editor.exe"; Flags: nowait; Check: IsUpdate

[Code]
function IsUpdate: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;

procedure InitializeWizard;
begin
  WizardForm.Caption := 'GoreeCloud Rich Text Editor';
end;
