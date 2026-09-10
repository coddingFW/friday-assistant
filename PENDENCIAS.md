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
- [x] **Escrita/edição de arquivos** com confirmação, restrita à raiz, com backup
      (set/2026, ADR-0014) — editor manual no `WorkspacePanel` (lápis → `FileEditor`),
      `POST /api/workspace/file`, gate `FRIDAY_WORKSPACE_WRITE_ENABLED`. Trava
      salvar quando o arquivo veio truncado. Validado ao vivo.
- [ ] Apagar/renomear arquivo (cada um com confirmação própria).
- [ ] Aplicar bloco de código proposto pela Friday direto no arquivo (diff + confirmação).
- [ ] Busca no código exposta na UI (endpoint `search` já existe no backend).

## Chat — pré-visualização de mockups (concluído — ADR-0015)
- [x] Blocos ```html/```svg viram **preview ao vivo** no chat (iframe sandboxed,
      toggle Visualização/Código, largura desktop/mobile, tela cheia). O
      `code_system_prompt` pede mockup como HTML único autocontido. Validado ao vivo.
- [ ] Auto-altura do iframe (via `postMessage`) e "abrir no editor" a partir da prévia.

## Higiene
- [x] Organizar o trabalho não commitado em commits (set/2026) — Fases 9 e 10 +
      voz(mute)/lightbox subiram em 3 commits (`fee4f96` backend, `1bd2dc4`
      frontend, `67d5986` docs) e foram para o GitHub.
