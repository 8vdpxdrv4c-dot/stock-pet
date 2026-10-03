#define AppName "橘猫桌面助手"
#define AppExe "StockPet.exe"
[Setup]
AppId={{B6385627-42B5-49AE-9245-BEA69B9CBA7C}
AppName={#AppName}
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\StockPet
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=StockPet-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
[Languages]
Name: "chinesesimp"; MessagesFile: "packaging\ChineseSimplified.isl"
[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; Flags: unchecked
Name: "startup"; Description: "开机自启动（可在程序设置中关闭）"; Flags: unchecked
[Files]
Source: "dist\StockPet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "StockPet"; ValueData: """{app}\{#AppExe}"""; Tasks: startup; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "StockPet"; Flags: uninsdeletevalue
[Run]
Filename: "{app}\{#AppExe}"; Description: "启动橘猫桌面助手"; Flags: nowait postinstall skipifsilent
