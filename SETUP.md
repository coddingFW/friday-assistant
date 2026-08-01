# SETUP — Preparar o Friday em uma máquina nova

O código e a documentação viajam pelo OneDrive/Git; o **ambiente** (venv,
node_modules, programas) é recriado por máquina. Este guia (e o `setup.ps1`)
fazem isso rapidamente.

## ⚠️ OneDrive
O OneDrive sincroniza a pasta inteira e **ignora o `.gitignore`**. Ele tentará
sincronizar `.venv/`, `frontend/node_modules/` e `frontend/src-tauri/target/` —
o que causa lentidão, cópias de conflito e venvs quebrados. Recomendado:
- mover o projeto para fora do OneDrive (ex.: `C:\dev\friday`) e usar Git; ou
- excluir aquelas três pastas da sincronização do OneDrive e **não** rodar
  `pip`/`npm`/build enquanto o OneDrive estiver sincronizando.

## Pré-requisitos (instalar uma vez por máquina)
| Programa | Para quê | Instalar |
|---|---|---|
| **Python 3.12+** | backend | https://python.org (ou winget `Python.Python.3.12`) |
| **Node.js 18+** | frontend | https://nodejs.org (ou winget `OpenJS.NodeJS`) |
| **Ollama** | LLM local | `winget install Ollama.Ollama` + `ollama pull llama3.1:8b` |
| **Rust** (opcional) | compilar o desktop Tauri | `winget install Rustlang.Rustup` |
| **VS Build Tools + WebView2** (opcional) | compilar o desktop no Windows | VS Build Tools 2022 c/ "Desktop C++"; WebView2 já vem no Win11 |

## Setup rápido (recomendado)
No PowerShell, dentro de `assistant-ai/`:
```powershell
./setup.ps1
```
O script cria o `.venv`, instala as dependências do backend e do frontend, e
verifica o Ollama e o modelo. É idempotente — pode rodar de novo sem problema.

## Setup manual (equivalente)
```bash
# Backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements-dev.txt

# Frontend
cd frontend
npm install
```

## Rodar
```bash
# Backend (na raiz assistant-ai/)
uvicorn backend.main:app --reload
```
```bash
# Frontend web (em frontend/)
npm run dev            # http://127.0.0.1:1420
```
Desktop Tauri (exige Rust): `npm run tauri dev` / `npm run tauri build`.

## Verificar que está tudo certo
```bash
pytest                                   # backend: suíte verde
curl http://127.0.0.1:8000/api/health    # llm_reachable: true com Ollama no ar
```

## Continuidade do projeto
Ao reabrir, leia **`PROJECT_MANIFEST.md`** + o último **`PHASE_REPORTS/`** + os
**`ADR/`** para reconstruir o estado (Fases 0–3 concluídas até aqui).
