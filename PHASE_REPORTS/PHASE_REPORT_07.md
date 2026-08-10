# PHASE_REPORT_07 — Conversa contínua (mãos-livres) + wake word

## Objetivos
Fechar o ciclo de voz: conversar sem clicar (mic contínuo), a Friday respondendo
só quando chamada pelo nome (wake word), e sem reagir à própria voz (anti-eco).

## Arquivos criados
- `frontend/src/services/wakeWord.ts` — detecção da wake word na transcrição, com
  tolerância à grafia do Whisper (variantes de "Friday").
- `ADR/ADR-0010.md`.

## Arquivos modificados
- `frontend/src/hooks/useChat.ts` — modo **mãos-livres**: mic contínuo que pausa
  durante o turno/fala; handler de `transcript` com **gating anti-eco**
  (`turnActive || speaking`); wake word (checa/retira o nome antes de enviar);
  `setMic` idempotente que controla o mic e o indicador.
- `frontend/src/components/Composer.tsx` — toggle **Mãos-livres**, campo da wake
  word e "exigir nome"; o mic manual fica desabilitado no modo mãos-livres.
- `frontend/src/App.tsx` — fiação dos novos controles.
- `frontend/src/styles.css` — estilos dos controles de voz.
- `PROJECT_MANIFEST.md` — Fase 7 marcada.

## Decisões de arquitetura
**ADR-0010**: loop orquestrado no cliente (reusa mic/transcrição/`send`); wake
word por transcrição (sem chave — Porcupine descartado pela restrição do
manifesto); anti-eco no cliente (ignora transcrição durante turno/fala).

## Como validado
- **Frontend:** `tsc --noEmit` limpo; build de produção ok.
- **Backend:** inalterado (suíte segue verde).
- **Fluxo revisado:** ligar mãos-livres → mic on; "Friday, <pergunta>" → envia o
  comando; durante processar/falar o mic é ignorado (anti-eco); ao terminar,
  volta a ouvir.

## Limitações / pendências
- **Validação falada real (usuário):** ajustar sensibilidade da wake word conforme
  o STT transcreve seu "Friday".
- Durante o turno o backend ainda transcreve o eco (sem efeito no cliente, mas
  gasta CPU) — pausar o mic no Host durante o turno pede rodar o turno como task
  (não bloquear o laço do WS); fica como evolução.
- Sem detecção dedicada de wake word (openWakeWord) — evolução futura.

## Checklist
- [x] Modo mãos-livres (mic contínuo)
- [x] Wake word por transcrição, tolerante à grafia, configurável
- [x] Anti-eco (pausa o mic + ignora transcrição durante turno/fala)
- [x] UI: toggle mãos-livres + wake word; mic manual desabilitado no modo
- [x] tsc limpo, build ok
- [ ] Validação falada real + ajuste fino
