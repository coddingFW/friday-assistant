# setup.ps1 - Bootstrap do ambiente do Friday (idempotente).
# Uso (PowerShell, dentro de assistant-ai/):  ./setup.ps1
# Recria o venv do backend, instala dependencias de backend e frontend e
# verifica o Ollama. Nao instala programas de sistema (Python/Node/Ollama/Rust).
# Observacao: mantido em ASCII de proposito (PowerShell 5.1 le .ps1 como ANSI).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Write-Note($msg) { Write-Host "  [!] $msg" -ForegroundColor Yellow }

# --- 1. Pre-requisitos minimos ---------------------------------------------
Write-Step "Verificando Python e Node"
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { throw "Python nao encontrado no PATH. Instale Python 3.12+." }
Write-Ok "Python: $((python --version) 2>&1)"

$node = (Get-Command node -ErrorAction SilentlyContinue)
if (-not $node) { Write-Note "Node nao encontrado - o frontend sera pulado." }
else { Write-Ok "Node: $((node --version) 2>&1)" }

# --- 2. Backend: venv + dependencias ---------------------------------------
Write-Step "Backend (.venv + dependencias)"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
    Write-Ok "venv criado"
} else {
    Write-Ok "venv ja existe"
}
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $root "requirements-dev.txt")
Write-Ok "dependencias do backend instaladas"

# --- 3. Frontend: node_modules ---------------------------------------------
if ($node) {
    Write-Step "Frontend (npm install)"
    Push-Location (Join-Path $root "frontend")
    npm install
    Pop-Location
    Write-Ok "dependencias do frontend instaladas"
}

# --- 4. Ollama (servico + modelo) ------------------------------------------
Write-Step "Ollama"
try {
    $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
    $models = @($tags.models | ForEach-Object { $_.name })
    Write-Ok "servico no ar. Modelos: $([string]::Join(', ', $models))"
    if ($models -notcontains "llama3.1:8b") {
        Write-Note "Modelo padrao ausente. Rode:  ollama pull llama3.1:8b"
    }
} catch {
    Write-Note "Ollama nao respondeu em :11434. Abra o Ollama e rode:  ollama pull llama3.1:8b"
}

# --- 5. Proximos passos -----------------------------------------------------
Write-Step "Pronto! Proximos passos"
Write-Host "  Backend:   uvicorn backend.main:app --reload"
Write-Host "  Frontend:  cd frontend; npm run dev   (http://127.0.0.1:1420)"
Write-Host "  Testes:    .\.venv\Scripts\python.exe -m pytest"
