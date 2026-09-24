<#
  Збірка інсталятора Viewer-for-School.

  Версія береться з файлу VERSION у корені репозиторію (єдине джерело правди).
  Приклади:
    powershell -ExecutionPolicy Bypass -File installer\build.ps1
    powershell -ExecutionPolicy Bypass -File installer\build.ps1 -Version 1.2.0

  Результат: installer\Output\Viewer-for-School-Setup-<версія>.exe
#>
param(
    [string]$Version = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot      # корінь репозиторію

if (-not $Version) {
    $verFile = Join-Path $root 'VERSION'
    if (-not (Test-Path $verFile)) {
        throw "Не знайдено файл версії: $verFile"
    }
    $Version = (Get-Content $verFile -Raw).Trim()
    if (-not $Version) {
        throw "Файл версії порожній: $verFile"
    }
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Некоректна версія '$Version' (очікується формат X.Y.Z)"
}

# --- знайти ISCC.exe (Inno Setup 6) -----------------------------------------
$iscc = $null
$candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
) | Where-Object { $_ -and (Test-Path $_) }

if ($candidates) {
    $iscc = $candidates | Select-Object -First 1   # масив може бути елементом
} else {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    throw "ISCC.exe не знайдено. Встановіть Inno Setup 6: winget install JRSoftware.InnoSetup"
}

$iss = Join-Path $PSScriptRoot 'viewer_setup.iss'
Write-Host "Inno Setup : $iscc"
Write-Host "Скрипт     : $iss"
Write-Host "Версія     : $Version"

& $iscc "/DAppVersion=$Version" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Компіляція завершилася з кодом $LASTEXITCODE"
}

$exe = Join-Path $PSScriptRoot "Output\Viewer-for-School-Setup-$Version.exe"
if (-not (Test-Path $exe)) {
    throw "Файл не створено: $exe"
}
Write-Host "Готово: $exe ($([math]::Round((Get-Item $exe).Length / 1MB, 1)) МБ)"
