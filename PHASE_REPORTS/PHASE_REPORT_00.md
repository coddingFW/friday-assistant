# PHASE_REPORT_00 — Arquitetura (Fase 0)

## Objetivos
Definir a arquitetura completa antes de qualquer código: requisitos, escolhas
tecnológicas justificadas, camadas, fluxos, padrões, riscos e documentação base.

## Entregas
- Topologia **Host + Clientes finos** definida.
- Escolhas aprovadas: Frontend **Tauri 2.0 + React** (ADR-0001), LLM **Ollama**
  com modelo configurável + STT **faster-whisper** (ADR-0002), TTS **Piper** (ADR-0003).
- Arquitetura em camadas e fluxo do loop contínuo desenhados (ASCII).
- Padrões definidos: Ports & Adapters, Strategy, Repository, DI.

## Arquivos criados
Nenhum de código. Apenas documentos (nesta e na Fase 1): `PROJECT_MANIFEST.md`,
`ADR-0001/0002/0003.md`, este relatório.

## Riscos identificados
Setup do Tauri (Rust/WebView2); peso de Ollama/Whisper; mobile offline inviável
para IA (mitigado pela topologia Host+Cliente); instabilidade do DuckDuckGo (RAG).

## Checklist
- [x] Requisitos e requisito de portabilidade compreendidos
- [x] Tecnologias comparadas e escolhidas com justificativa
- [x] Arquitetura e fluxos desenhados
- [x] ADRs e manifesto aprovados
- [x] Aprovação do arquiteto (`APROVADA`)

## Pendências
Nenhuma. Fase 0 aprovada; Fase 1 autorizada.
