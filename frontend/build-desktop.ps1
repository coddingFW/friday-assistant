# build-desktop.ps1 - Compila o app desktop Tauri no Windows.
#
# Encapsula as tres condicoes necessarias descobertas em teste real:
#   1. cargo no PATH (rustup instala em %USERPROFILE%\.cargo\bin);
#   2. ambiente MSVC carregado (vcvars64) para o rustc achar link.exe + Windows SDK;
#   3. CARGO_TARGET_DIR FORA do OneDrive (o sync trava os arquivos do build ->
#      "output path is not a writable directory").
#
# Uso (PowerShell, dentro de frontend/):
#   ./build-desktop.ps1              # build + instaladores (bundle)
#   ./build-desktop.ps1 --no-bundle  # apenas o executavel (mais rapido)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. cargo no PATH
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"

# 2. target do Rust fora do OneDrive (caminho local, sem espacos, sem sync)
if (-not $env:CARGO_TARGET_DIR) {
    $env:CARGO_TARGET_DIR = Join-Path $env:LOCALAPPDATA "friday-build"
}
Write-Host "CARGO_TARGET_DIR = $($env:CARGO_TARGET_DIR)" -ForegroundColor Cyan

# 3. Ambiente MSVC via vswhere (portavel entre maquinas)
$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "vswhere nao encontrado. Instale o Visual Studio Build Tools." }
$vsPath = & $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
if (-not $vsPath) {
    throw "VS com C++ nao encontrado. Instale o workload 'Desktop development with C++' (traz MSVC + Windows SDK)."
}
$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
Write-Host "vcvars = $vcvars" -ForegroundColor Cyan

# 4. Build dentro do ambiente MSVC (o cmd filho herda PATH e CARGO_TARGET_DIR)
Set-Location $root
$tauriArgs = $args -join ' '
cmd /c "`"$vcvars`" >nul && npm run tauri build -- $tauriArgs"
if ($LASTEXITCODE -ne 0) { throw "Build falhou (exit $LASTEXITCODE)." }
Write-Host "`nBuild concluido. Binario em: $($env:CARGO_TARGET_DIR)\release\" -ForegroundColor Green
