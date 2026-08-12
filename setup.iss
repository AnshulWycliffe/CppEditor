; CppEditor Inno Setup Script
[Setup]
AppName=CppEditor
AppVersion=2.0
DefaultDirName={autopf}\CppEditor
DefaultGroupName=CppEditor
UninstallDisplayIcon={app}\CppEditor.exe
OutputDir=dist
OutputBaseFilename=CppEditorInstaller
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
LicenseFile=license.txt

[Files]
Source: "CppEditor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "logo.ico"; DestDir: "{app}"
Source: "winlibs\*"; DestDir: "{app}\winlibs"; Flags: recursesubdirs ignoreversion
Source: "license.txt"; DestDir: "{app}"

[Icons]
Name: "{group}\CppEditor"; Filename: "{app}\CppEditor.exe"; IconFilename: "{app}\logo.ico"
Name: "{userdesktop}\CppEditor"; Filename: "{app}\CppEditor.exe"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\CppEditor.exe"; Description: "Launch CppEditor"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
ValueType: expandsz; ValueName: "Path"; \
ValueData: "{olddata};{app}\winlibs\bin"; Flags: preservestringtype