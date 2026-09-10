# Pendências — Friday

Lista viva de itens a verificar/fazer depois. Não é roadmap de arquitetura (isso
está no `PROJECT_MANIFEST.md`); é o backlog prático entre fases.

## TTS — fonética / pronúncia (a verificar)
**Sintoma relatado (set/2026):** a voz parece errar palavras com dígrafos e
acentos, "mudando a sílaba tônica".

**Diagnóstico já feito (não refazer):**
- O encoding está correto: o `PiperTTSProvider` envia UTF-8 + `PYTHONUTF8=1`
  (`backend/tts/providers/piper.py`). `to_speech_text` preserva acentos.
- Fonemizei ~45 palavras (incl. hiatos, nasais, dígrafos: país, saída, memória,
  espanhol, função, difícil…) via o espeak-ng do Piper: **a tônica sai correta em
  todas**. Ou seja, a camada de fonemas/tônica está certa — não é o nosso código
  nem falha sistemática do espeak.
- Suspeitos restantes: (1) **renderização da voz `faber-medium`** (prosódia fraca
  pode fazer a tônica correta *soar* errada); (2) **sotaque dos dígrafos** do
  espeak BR (`carro`→"cáhu", `difícil`→"dificiu", `r` inicial→"h") — correto, mas
  pode não ser o esperado.

**Próximos passos:**
- [ ] Coletar do usuário 2–3 **palavras/frases concretas** que soam erradas.
- [ ] Fonemizar cada uma e classificar: tônica × dígrafo × timbre.
- [ ] Se pontual: criar **dicionário de pronúncia** (correção por palavra em
      `to_speech_text`, verificável pelos fonemas, sem depender de ouvir).
- [ ] A/B de vozes: baixar `pt_BR-cadu-medium` / `pt_BR-jeff-medium` e comparar de
      ouvido (troca via `FRIDAY_PIPER_VOICE`).

## Fase 9 — memória longa (frontend concluído)
- [x] **Barra lateral de histórico** (listar/retomar/apagar conversas, consumindo
      `GET/DELETE /api/conversations` e enviando `conversation_id` no WS) — botão
      "Histórico" no header, painel `HistoryPanel`, "nova conversa" + retomar +
      apagar. Ver `PHASE_REPORT_09.md` › Frontend.
- [x] Polimento: auto-atualizar `message_count`/título ao fim do turno — o `App`
      recarrega o histórico ~500ms após o `idle` (o backend persiste o turno logo
      após emitir `idle`; o atraso evita a corrida). O botão recarregar continua.

## Fase 8 — visão (incrementos)
- [ ] Validar a qualidade do `minicpm-v` no uso real (troca de `llava` feita).
- [ ] Webcam (StreamingSensor via opencv) e OCR dedicado (tesseract) — ADR próprio.

## Fase 10 — workspace (evolução)
- [ ] **Escrita/edição de arquivos** com confirmação, restrita à raiz, backup/git.
- [ ] Busca no código exposta na UI (endpoint `search` já existe no backend).

## Higiene
- [ ] Organizar o trabalho não commitado em commits (Fases 9 e 10 + visão/identidade
      + lightbox + mute).
