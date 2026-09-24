; ============================================================
;  Viewer-for-School — скрипт інсталятора (Inno Setup 6+)
;
;  Збірка:  installer\build.ps1                     (звичайний шлях)
;           ISCC.exe /DAppVersion=1.1.0 installer\viewer_setup.iss
;  Ресурси: installer\make_assets.py → app.ico, wizard.png, wizard-small.png
;
;  Модель: portable — додаток ставиться у вибрану теку (корінь навчальної
;  теки з матеріалами); viewer.html і viewer_assets/ генеруються на місці;
;  деінсталяція не чіпає матеріали.
; ============================================================

#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

#define ProductName "Viewer-for-School"
#define Publisher   "FileViewer-for-students-and-teachers"
#define AppGuid     "{{7C1E5A24-3B48-4E77-9A2C-5F0D6B8E1A33}"

[Setup]
AppId={#AppGuid}
AppName={#ProductName}
AppVersion={#AppVersion}
AppVerName={#ProductName} {#AppVersion}
AppPublisher={#Publisher}
AppCopyright=Copyright (c) 2026 {#Publisher}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#ProductName}
VersionInfoCompany={#Publisher}
VersionInfoDescription={#ProductName} - переглядач навчальних матеріалів 11-Д
DefaultDirName={userdocs}\{#ProductName}
DefaultGroupName={#ProductName}
DisableProgramGroupPage=yes
AppendDefaultDirName=no
DirExistsWarning=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename={#ProductName}-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardImageFile=wizard.png
WizardSmallImageFile=wizard-small.png
SetupIconFile=app.ico
LicenseFile=..\LICENSE.txt
InfoBeforeFile=requirements_note.txt
MinVersion=10.0
UninstallDisplayIcon={app}\app.ico
UninstallDisplayName={#ProductName} {#AppVersion}

[Languages]
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
ukrainian.SelectDirDesc=Встановіть додаток у КОРІНЬ навчальної теки з матеріалами (де лежать папки предметів: «01 Ukr mova», «07 Matematuka» тощо)
english.SelectDirDesc=Install into the ROOT of the study folder with the materials (the folder that contains "01 Ukr mova", "07 Matematuka" etc.)

[CustomMessages]
ukrainian.TaskDeps=Доставити Python-залежності (pip --user; потрібен інтернет)
english.TaskDeps=Install Python dependencies (pip --user; internet required)
ukrainian.TaskFirstGen=Згенерувати viewer.html для цієї теки одразу (рекомендовано; може тривати кілька хвилин)
english.TaskFirstGen=Generate viewer.html for this folder now (recommended; may take minutes)
ukrainian.IconView=📚 Viewer-for-School — перегляд матеріалів
english.IconView=📚 Viewer-for-School — viewer
ukrainian.IconGen=⚙️ Згенерувати для теки…
english.IconGen=⚙️ Generate for a folder…
ukrainian.LaunchApp=Відкрити перегляд матеріалів
english.LaunchApp=Open the viewer
ukrainian.StatusDeps=Перевіряю та доставляю Python-залежності…
english.StatusDeps=Checking and installing Python dependencies…
ukrainian.AskInstallPython=Python 3.8+ не знайдено — без нього не працює генерація сторінки.%n%nТА — завантажити та встановити Python автоматично (інтернет, ~32 МБ, без прав адміністратора);%nНІ — відкрити офіційну сторінку завантаження;%nСКАСУВАТИ — продовжити без Python (кнопки «🔄 Оновити файли» не буде).
english.AskInstallPython=Python 3.8+ was not found — page generation will not work without it.%n%nYES — download and install Python automatically (internet, ~32 MB, no admin rights);%nNO — open the official download page;%nCANCEL — continue without Python (there will be no "🔄 Refresh files" button).
ukrainian.StatusPython=Завантажую та встановлюю Python…
english.StatusPython=Downloading and installing Python…
ukrainian.PythonFailed=Не вдалося встановити Python автоматично.%nВідкриваю офіційну сторінку завантаження — встановіть Python уручну (поставте галочку «Add python.exe to PATH»).
english.PythonFailed=Could not install Python automatically.%nOpening the official download page — please install Python manually (tick "Add python.exe to PATH").
ukrainian.NoOffice=Microsoft Office не знайдено:%n• .pptx показуватимуться без JPG-слайдів (лише текст і структура);%n• для .docx не буде PDF-прев'ю (лише HTML-режим).%n%nOffice встановлюється окремо — інсталятор не має права робити це автоматично (ліцензія).
english.NoOffice=Microsoft Office was not found:%n• .pptx slides will be shown without JPG images (text and structure only);%n• no PDF preview for .docx (HTML mode only).%n%nOffice is installed separately — the installer cannot do it automatically (license).
ukrainian.NoFfmpeg=ffmpeg не знайдено: файли .avi відкриватимуться окремо, без конвертації у .mp4.%n%nВстановити ffmpeg зараз через winget (~100 МБ, інтернет)?%n«Ні» — пропустити (посилання: https://ffmpeg.org/download.html)
english.NoFfmpeg=ffmpeg was not found: .avi files will open separately, without conversion to .mp4.%n%nInstall ffmpeg now via winget (~100 MB, internet)?%n"No" — skip (link: https://ffmpeg.org/download.html)
ukrainian.StatusFfmpeg=Встановлюю ffmpeg (winget)…
english.StatusFfmpeg=Installing ffmpeg (winget)…
ukrainian.FfmpegFailed=Не вдалося встановити ffmpeg через winget.%nПосилання: https://ffmpeg.org/download.html
english.FfmpegFailed=Could not install ffmpeg via winget.%nLink: https://ffmpeg.org/download.html
ukrainian.BadDir=У цю теку додаток не зможе писати viewer.html і viewer_assets/.%nОберіть корінь навчальної теки з матеріалами (наприклад, у Документах або на іншому диску).
english.BadDir=The app cannot write viewer.html and viewer_assets/ into this folder.%nChoose the root of the study folder with the materials (e.g. in Documents or on another drive).
ukrainian.NoWrite=Немає прав на запис у цю теку. Оберіть іншу теку.
english.NoWrite=No write access to this folder. Please choose another one.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "deps"; Description: "{cm:TaskDeps}"
Name: "firstgen"; Description: "{cm:TaskFirstGen}"; Flags: checkedonce

[Files]
Source: "..\generate_viewer.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\viewer_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\viewer_probe.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start_viewer.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\generate_for.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\install_deps.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\viewer_help.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{cm:IconView}"; Filename: "{app}\start_viewer.bat"; WorkingDir: "{app}"
Name: "{group}\{cm:IconGen}"; Filename: "{app}\generate_for.bat"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#ProductName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{cm:IconView}"; Filename: "{app}\start_viewer.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; 1) Python-залежності (pip --user) — лише якщо вибрано завдання і є Python
Filename: "{code:GetPythonExe}"; Parameters: """{app}\install_deps.py"""; WorkingDir: "{app}"; StatusMsg: "{cm:StatusDeps}"; Flags: runhidden waituntilterminated; Tasks: deps; Check: PythonAvailable
; 2) Перша генерація сторінки для цієї теки (видно прогрес у консолі)
Filename: "{code:GetPythonExe}"; Parameters: """{app}\generate_viewer.py"" ""{app}"""; WorkingDir: "{app}"; StatusMsg: "{cm:TaskFirstGen}"; Flags: waituntilterminated; Tasks: firstgen; Check: PythonAvailable
; 3) Запуск переглядача
Filename: "{app}\start_viewer.bat"; Description: "{cm:LaunchApp}"; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
; Прибираємо лише власні файли стану; viewer.html і viewer_assets/ не чіпаємо
Type: files; Name: "{app}\viewer_server.port"
Type: files; Name: "{app}\viewer_server.log"
Type: files; Name: "{app}\viewer_server.prev.log"

[Code]
const
  { Офіційний інсталтор Python для Windows x64. SHA-256 звірено двічі:
    таблиця на python.org/downloads/release/python-3147 (колонка SHA-256)
    і winget-мейнфест manifests/p/Python/Python/3/14/3.14.7 }
  PythonDlUrl       = 'https://www.python.org/ftp/python/3.14.7/python-3.14.7-amd64.exe';
  PythonDlSha256    = '9D9EB2709EF81BF5CD30DB3C2096BDBC4EA10087C22E62F27D356B36F6AE9649';
  WingetPythonId    = 'Python.Python.3.14';
  WingetFfmpegId    = 'Gyan.FFmpeg.Essentials';
  PythonDownloadPage = 'https://www.python.org/downloads/';

var
  PythonExe: String;

{ Текст із CustomMessage, у якому %n гарантовано → переклад рядка.
  MsgBox сам по собі %n не інтерпретує — розгортаємо вручну. }
function MsgText(const Key: String): String;
begin
  Result := CustomMessage(Key);
  StringChangeEx(Result, '%n', #13#10, True);
end;

function GetPythonExe(Param: String): String;
begin
  Result := PythonExe;
end;

function PythonAvailable(): Boolean;
begin
  Result := PythonExe <> '';
end;

{ «3.12», «3.13-32», «2.7» → чи підходить версія (мін. 3.8) }
function VersionNumberOk(const Ver: String): Boolean;
var
  S: String;
  Major, Minor, P: Integer;
begin
  Result := False;
  S := Ver;
  P := Pos('-', S);
  if P > 0 then S := Copy(S, 1, P - 1);
  P := Pos('.', S);
  if P = 0 then Exit;
  Major := StrToIntDef(Copy(S, 1, P - 1), -1);
  S := Copy(S, P + 1, Length(S));
  P := Pos('.', S);
  if P > 0 then S := Copy(S, 1, P - 1);
  Minor := StrToIntDef(S, -1);
  Result := (Major > 3) or ((Major = 3) and (Minor >= 8));
end;

{ Пошук Python у реєстрі: HKLM і HKCU (per-user), усі версії-підключі }
function FindPythonInRegistry(): String;
var
  Hives: array[0..1] of Integer;
  Roots: array[0..1] of String;
  Subs: TArrayOfString;
  i, j: Integer;
  Base, Path, Ver, Exe: String;
begin
  Result := '';
  Hives[0] := HKEY_LOCAL_MACHINE; Roots[0] := 'SOFTWARE\Python\PythonCore';
  Hives[1] := HKEY_CURRENT_USER;  Roots[1] := 'SOFTWARE\Python\PythonCore';
  for i := 0 to 1 do
  begin
    Base := Roots[i];
    if RegGetSubkeyNames(Hives[i], Base, Subs) then
      for j := 0 to GetArrayLength(Subs) - 1 do
      begin
        Ver := Subs[j];
        if VersionNumberOk(Ver) then
        begin
          Path := '';
          if RegQueryStringValue(Hives[i], Base + '\' + Ver + '\InstallPath', '', Path) then
            if Path <> '' then
            begin
              if Copy(Path, Length(Path), 1) <> '\' then Path := Path + '\';
              Exe := Path + 'python.exe';
              if FileExists(Exe) then
              begin
                Result := Exe;
                Exit;
              end;
            end;
        end;
      end;
  end;
end;

{ Пошук exe у PATH (заглушку WindowsApps з Магазину пропускаємо) }
function FindExeOnPath(const ExeName: String): String;
var
  Rest, Token, Exe: String;
  P: Integer;
begin
  Result := '';
  Rest := GetEnv('PATH');
  while Rest <> '' do
  begin
    P := Pos(';', Rest);
    if P > 0 then
    begin
      Token := Copy(Rest, 1, P - 1);
      Rest := Copy(Rest, P + 1, Length(Rest));
    end
    else
    begin
      Token := Rest;
      Rest := '';
    end;
    Token := Trim(Token);
    if (Token <> '') and (Pos('WINDOWSAPPS', Uppercase(Token)) = 0) then
    begin
      if Copy(Token, Length(Token), 1) <> '\' then Token := Token + '\';
      Exe := Token + ExeName;
      if FileExists(Exe) then
      begin
        Result := Exe;
        Exit;
      end;
    end;
  end;
end;

function FindPythonInPath(): String;
begin
  Result := FindExeOnPath('python.exe');
end;

function FindPython(): String;
begin
  Result := FindPythonInRegistry();
  if Result = '' then
    Result := FindPythonInPath();
end;

{ Чи можна писати у теку (додаток створює там viewer.html і viewer_assets) }
function HasWriteAccess(const Dir: String): Boolean;
var
  TestFile: String;
begin
  TestFile := Dir;
  if Copy(TestFile, Length(TestFile), 1) = '\' then
    TestFile := TestFile + '.viewer_write_test.tmp'
  else
    TestFile := TestFile + '\.viewer_write_test.tmp';
  Result := SaveStringToFile(TestFile, 'test', False);
  if Result then
    DeleteFile(TestFile);
end;

function SameOrInside(const Dir, Parent: String): Boolean;
var
  D, P: String;
begin
  D := Uppercase(Dir);
  P := Uppercase(Parent);
  Result := (D = P) or (Copy(D, 1, Length(P) + 1) = P + '\');
end;

{ Program Files / Windows — не можна: там немає прав на запис }
function IsBadTarget(const Dir: String): Boolean;
begin
  Result := SameOrInside(Dir, ExpandConstant('{commonpf}'))
         or SameOrInside(Dir, ExpandConstant('{commonpf32}'))
         or SameOrInside(Dir, ExpandConstant('{win}'))
         or SameOrInside(Dir, ExpandConstant('{sys}'));
end;

function InitializeSetup(): Boolean;
begin
  PythonExe := FindPython();
  Log('Viewer-for-School: Python = ' + PythonExe);
  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID <> wpSelectDir then
    Exit;
  if IsBadTarget(WizardDirValue) then
  begin
    MsgBox(MsgText('BadDir'), mbError, MB_OK);
    Result := False;
    Exit;
  end;
  if DirExists(WizardDirValue) and (not HasWriteAccess(WizardDirValue)) then
  begin
    MsgBox(MsgText('NoWrite'), mbError, MB_OK);
    Result := False;
  end;
end;

procedure SetStatusText(const Msg: String);
begin
  try
    WizardForm.StatusLabel.Caption := Msg;
  except
    // сторінка прогресу ще не показана — підпис не критичний
  end;
end;

{ Чи зареєстровані COM-сервери Word і PowerPoint (потрібні для прев'ю) }
function OfficeInstalled(): Boolean;
begin
  Result := RegKeyExists(HKEY_CLASSES_ROOT, 'Word.Application\CurVer')
        and RegKeyExists(HKEY_CLASSES_ROOT, 'PowerPoint.Application\CurVer');
end;

function FfmpegFound(): Boolean;
begin
  Result := FindExeOnPath('ffmpeg.exe') <> '';
end;

{ winget із типовими «тихими» згодами }
function RunWinget(const PackageId: String): Boolean;
var
  ErrCode: Integer;
begin
  ErrCode := 0;
  Result := Exec('winget.exe',
    'install --exact --id ' + PackageId +
    ' --silent --accept-source-agreements --accept-package-agreements' +
    ' --disable-interactivity', '', SW_HIDE, ewWaitUntilTerminated, ErrCode)
    and (ErrCode = 0);
end;

{ Прогрес завантаження Python (викликається з DownloadTemporaryFile) }
function OnDlProgress(const Url, FileName: String;
  const Progress, ProgressMax: Int64): Boolean;
begin
  try
    if ProgressMax > 0 then
      WizardForm.StatusLabel.Caption :=
        Format('%s — %d%%', [FileName, (Progress * 100) div ProgressMax])
    else
      WizardForm.StatusLabel.Caption := Format('%s — %d KB', [FileName, Progress div 1024]);
  except
  end;
  Result := True;                         { True — продовжити завантаження }
end;

{ Авто-встановлення Python: python.org (перевірка SHA-256) → фолбек winget }
function InstallPythonFromWeb(): Boolean;
var
  ErrCode: Integer;
begin
  Result := False;
  try
    DownloadTemporaryFile(PythonDlUrl, 'python-setup.exe', PythonDlSha256,
                          @OnDlProgress);
    ErrCode := 0;
    if Exec(ExpandConstant('{tmp}\python-setup.exe'),
            '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1' +
            ' Include_pip=1 Shortcuts=0 AssociateFiles=0',
            '', SW_HIDE, ewWaitUntilTerminated, ErrCode) and (ErrCode = 0) then
      Result := True;
  except
    Log('Viewer-for-School: python.org download failed: ' +
        GetExceptionMessage);
  end;
  if not Result then
    Result := RunWinget(WingetPythonId);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Ans, Res: Integer;
begin
  { ssInstall — до копіювання файлів і [Run]: завдання «залежності» та
    «перша генерація» побачать уже оновлений PythonExe }
  if (CurStep = ssInstall) and (PythonExe = '') then
  begin
    if WizardSilent() then
      Log('Viewer-for-School: Python not found; silent mode, no prompt')
    else
    begin
      Ans := MsgBox(MsgText('AskInstallPython'), mbConfirmation, MB_YESNOCANCEL);
      if Ans = IDYES then
      begin
        SetStatusText(CustomMessage('StatusPython'));
        if not InstallPythonFromWeb() then
        begin
          MsgBox(MsgText('PythonFailed'), mbError, MB_OK);
          ShellExec('open', PythonDownloadPage, '', '', SW_SHOWNORMAL,
                    ewNoWait, Res);
        end;
        PythonExe := FindPython();
        Log('Viewer-for-School: after auto-install Python = ' + PythonExe);
      end
      else if Ans = IDNO then
        ShellExec('open', PythonDownloadPage, '', '', SW_SHOWNORMAL,
                  ewNoWait, Res)
      else
        Log('Viewer-for-School: Python prompt cancelled by user');
    end;
  end;

  { Office/ffmpeg: детекція + попередження; ffmpeg — ще й winget за згодою }
  if (CurStep = ssPostInstall) and (not WizardSilent()) then
  begin
    if not OfficeInstalled() then
      MsgBox(MsgText('NoOffice'), mbInformation, MB_OK);
    if not FfmpegFound() then
      if MsgBox(MsgText('NoFfmpeg'), mbConfirmation, MB_YESNO) = IDYES then
      begin
        SetStatusText(CustomMessage('StatusFfmpeg'));
        if not RunWinget(WingetFfmpegId) then
          MsgBox(MsgText('FfmpegFailed'), mbInformation, MB_OK);
      end;
  end;
end;