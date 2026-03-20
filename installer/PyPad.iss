#define MyAppName "PyPad"
#define MyAppPublisher "PyPad"
#define MyAppExeName "run.exe"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{4E6E3EFA-6F45-4D8F-BF1E-7AFD4382202A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=PyPad-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and x86compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "assoc_txt"; Description: "Associate .txt files with PyPad"; GroupDescription: "File associations:"; Flags: unchecked
Name: "ctx_openwith"; Description: "Add 'Open with PyPad' to file context menu"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
Source: "..\dist\run\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "_internal\PySide6\translations\qtwebengine_locales\*.pak,_internal\PySide6\translations\*.qm,_internal\PySide6\qml\*,_internal\PySide6\resources\qtwebengine_devtools_resources.pak,_internal\PySide6\resources\*.debug.pak,_internal\PySide6\resources\*.debug.bin,_internal\PySide6\plugins\platforms\qdirect2d.dll,_internal\PySide6\plugins\platforms\qminimal.dll,_internal\PySide6\plugins\platforms\qoffscreen.dll,_internal\PySide6\plugins\platforminputcontexts\qtvirtualkeyboardplugin.dll,_internal\PySide6\plugins\networkinformation\qnetworklistmanager.dll,_internal\PySide6\Qt6Positioning.dll,_internal\PySide6\QtPositioning.pyd,_internal\PySide6\Qt6Quick*.dll,_internal\PySide6\Qt6Qml*.dll,_internal\PySide6\QtQuick*.pyd,_internal\PySide6\QtQml*.pyd"
; Bundle Demo Pack templates so onboarding/help entries always have content after install.
Source: "..\templates\demo_pack\*"; DestDir: "{app}\templates\demo_pack"; Flags: ignoreversion recursesubdirs createallsubdirs
; Repo-local plugins are optional during packaging. The current build may ship none,
; and runtime/plugin onboarding still works via bundled online_plugins/catalog data.

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
; .txt association (optional)
Root: HKCU; Subkey: "Software\Classes\.txt"; ValueType: string; ValueName: ""; ValueData: "pypad.txtfile"; Flags: uninsdeletevalue; Tasks: assoc_txt
Root: HKCU; Subkey: "Software\Classes\pypad.txtfile"; ValueType: string; ValueName: ""; ValueData: "Text Document (PyPad)"; Flags: uninsdeletekey; Tasks: assoc_txt
Root: HKCU; Subkey: "Software\Classes\pypad.txtfile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey; Tasks: assoc_txt
Root: HKCU; Subkey: "Software\Classes\pypad.txtfile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: assoc_txt

; Context menu entry for all files (optional)
Root: HKCU; Subkey: "Software\Classes\*\shell\Open with PyPad"; ValueType: string; ValueName: ""; ValueData: "Open with PyPad"; Flags: uninsdeletekey; Tasks: ctx_openwith
Root: HKCU; Subkey: "Software\Classes\*\shell\Open with PyPad"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey; Tasks: ctx_openwith
Root: HKCU; Subkey: "Software\Classes\*\shell\Open with PyPad\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: ctx_openwith

[Code]
procedure RemovePyPadUserData();
var
  LegacyDir: string;
  PypadDir: string;
begin
  LegacyDir := ExpandConstant('{userappdata}\notepadclone');
  PypadDir := ExpandConstant('{userappdata}\pypad');

  if DirExists(LegacyDir) then
    DelTree(LegacyDir, True, True, True);
  if DirExists(PypadDir) then
    DelTree(PypadDir, True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Response: Integer;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;

  Response := MsgBox(
    'Do you want to remove PyPad settings and local app data?' + #13#10#13#10 +
    'Choose No to keep your settings, caches, reminders, and plugins for a future reinstall.' + #13#10 +
    'Choose Yes to delete only PyPad-managed data in your user AppData folders.',
    mbConfirmation,
    MB_YESNO or MB_DEFBUTTON2
  );

  if Response = IDYES then
    RemovePyPadUserData();
end;
