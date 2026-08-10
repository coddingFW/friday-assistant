# PHASE_REPORT_05 — Avatar (Fase 5)

## Objetivos
Adicionar um avatar sincronizado com a fala e com os estados da assistente, no
frontend, sem alterar o backend.

## Arquivos criados
- `frontend/src/services/audioPlayer.ts` — reprodução do áudio TTS roteada por um
  `AnalyserNode` (Web Audio); expõe `amplitude()`, `speaking` e `unlock()`.
- `frontend/src/components/Avatar3D.tsx` — **rosto 3D humano realista** (Three.js +
  modelo facecap): lip-sync pelo blendshape `jawOpen` (amplitude), piscar, balanço
  de cabeça, sobrancelhas em "pensando"; auto-enquadramento da câmera.
- `frontend/public/models/facecap.glb` (rosto real, MIT) + `public/basis/*`
  (transcoder KTX2). A versão SVG inicial foi criada e depois substituída pela 3D.

## Arquivos modificados
- `frontend/src/hooks/useChat.ts` — reproduz pelo `audioPlayer`; `unlock()` no envio.
- `frontend/src/components/MessageList.tsx` — botão "Ouvir" também via `audioPlayer`.
- `frontend/src/App.tsx` — insere o Avatar (palco acima das mensagens).
- `frontend/src/styles.css` — halo pulsante, blink, boca, indicador de "pensando".

## Dependências
- **`three`** (+ `@types/three`) — renderização 3D WebGL, offline.
- Web Audio API (nativa) para o lip-sync.
- Modelo `facecap.glb` (~326 KB) e transcoder basis em `public/` (não vêm do npm).

## Decisão de arquitetura
**ADR-0008**: avatar no cliente; expressão dirigida pelos eventos de `status` já
existentes; lip-sync pela **amplitude** do áudio (`AnalyserNode`). Backend
inalterado. Visemas ficam como evolução futura.

## Como validado
- **TypeScript** compila limpo (`tsc --noEmit`, exit 0).
- **Backend**: 47 testes verdes (inalterado nesta fase).
- **No navegador** (Vite + backend + Ollama + Piper): o avatar **renderiza**,
  muda de expressão conforme o status (visto "Buscando…"), recebe o áudio e
  reproduz **sem erros de console**; botão "Ouvir" presente.

## Limitações
- **Lip-sync não validado visualmente aqui**: no painel de navegador headless
  (sem compositação), `requestAnimationFrame` e o `AudioContext` ficam pausados,
  então a boca não anima no teste automatizado — precisa de um navegador exibido
  (validação visual/áudio do usuário).
- Lip-sync por amplitude é aproximado (não é preciso como visemas).
- O avatar é estilizado (SVG simples); trocar por sprite/Live2D é evolução.

## Checklist
- [x] Avatar no frontend (SVG)
- [x] Expressão por estado (idle/thinking/searching/responding)
- [x] Lip-sync por amplitude (Web Audio AnalyserNode)
- [x] Reprodução unificada pelo `audioPlayer` (autoplay + "Ouvir")
- [x] Autoplay robusto (`unlock()` no gesto do usuário)
- [x] Sem mudança no backend; TS limpo; testes verdes

## Pendências
- Validação visual/auditiva do usuário (ver o avatar animar a boca ao falar).
- (Futuro) lip-sync por visemas; expressões emocionais; avatar customizável.
