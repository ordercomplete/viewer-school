; viewer_setup.iss — Inno Setup скрипт для viewer

[Setup]
AppName=ViewerSchool 11-D
AppVersion=1.0
DefaultDirName={pf}\ViewerSchool
DefaultGroupName=ViewerSchool
OutputBaseFilename=ViewerSchoolSetup
Compression=lzma
SolidCompress=yes
LicenseFile=LICENSE.txt
InfoBeforeText=- Python 3.8+
- openpyxl
- python-pptx
- Pillow (PIL)

Якщо компоненти відсутні, інсталятор спробує їх встановити через pip.
WizardImageFile=wizard.bmp

[LangOptions]
DialogColor=0x003A6B
WizardSize=554x415

[CustomMessages]
LicenseDescription=Ця програма призначена для дистанційного заочного навчання старших класів середньої школи. Використовується безкоштовно як є, без претензій.
InfoBeforeLabel=Перед встановленням перевірте наявність:

[Files]
Source: "generate_viewer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "viewer_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "viewer_probe.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "start_viewer.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "viewer.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "viewer_help.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "__init__.py"; DestDir: "{app}\installer"

[Icons]
Name: "{group}\📚 Перегляд матеріалів"; Filename: "{app}\start_viewer.bat"
Name: "{group}\Згенерувати для теки..."; Filename: "cmd"; Parameters: "/k python ""{app}\generate_viewer.py"" "%~dp0"""

[Run]
Filename: "{cmd}"; Parameters: "/C pip install openpyxl python-pptx Pillow --quiet"; StatusMsg: "Встановлюються залежності..."; Flags: runhidden waituntilterminated
Filename: "{cmd}"; Parameters: "/C python --version"; Flags: runhidden; Check: not IsPythonInstalled

[Code]
function IsPythonInstalled(): Boolean
var reg: TRegistry; begin Result := False; reg := TRegistry.Create; try reg.RootKey := HKEY_LOCAL_MACHINE; if reg.OpenKeyReadOnly('SOFTWARE\Python\PythonCore', True) then begin if reg.KeyExists('3.8') or reg.KeyExists('3.9') or reg.KeyExists('3.10') or reg.KeyExists('3.11') or reg.KeyExists('3.12') then Result := true; end finally reg.Free end;end
function IsPythonExeAvailable(): Boolean begin Result := false end
function FindPythonExe(): String var pathVal: String; i, sep: Integer; token: String; begin Result := ''; pathVal := GetEnvVar('PATH'); i := 1; while i <= Length(pathVal) do begin sep := Pos(';', SubStr(pathVal, i)); if sep = 0 then token := SubStr(pathVal, i) else begin token := SubStr(pathVal, i, sep - 1); i := i + sep; end; if token = '' then continue; SetErrorMode(sem_noopenmsg); if FileExists(token + '\python.exe') then begin Result := token + '\python.exe'; Exit; end; end;end
function IsPythonVersionOk(pythonExe: String): Boolean var CmdOut: TExecResult; begin Run(pythonExe, '-V', '', swHide, arDefault, False, CmdOut); if CmdOut <> wrOK then exit(False); Result := Pos('3.8') > 0 or Pos('3.9') > 0 or Pos('3.10') > 0 or Pos('3.11') > 0 or Pos('3.12') > 0 end
procedure CurPageChanged(CurPageID: Integer); begin if CurPageID = wpWelcome then begin if not IsPythonInstalled() and not IsPythonExeAvailable() then WizardForm.WizardImages.Hide;end
function NextButtonClick(CurPageID: Integer): Boolean var pythonPath, pipResult: TExecResult; begin Result := True; if CurPageID = wpReady then begin if not IsPythonInstalled() then begin pythonPath := FindPythonExe(); if pythonPath <> '' and IsPythonVersionOk(pythonPath) then begin Run(pythonPath, '-m', 'pip install openpyxl python-pptx Pillow --quiet', '', swHide, arDefault, False, pipResult); end else begin MsgBox('Відсутній Python 3.8+. Спочатку встановіть Python з https://www.python.org/downloads/', mbError, MB_OK); Result := False; Exit; end; end end;end
