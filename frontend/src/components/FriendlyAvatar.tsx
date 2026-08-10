// Avatar amigável da Friday — estilo Avataaars (Pablo Stanley) via DiceBear,
// vetorial e 100% offline. Sem GLB. As partes (olhos, boca, sobrancelha) mudam
// conforme o estado e a voz: lip-sync trocando a boca pela amplitude do áudio,
// e "gestos" espontâneos (piscar, wink, língua) para dar personalidade.

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { createAvatar } from "@dicebear/core";
import { avataaars } from "@dicebear/collection";
import { audioPlayer } from "../services/audioPlayer";
import {
  configToOptions,
  getAvatarConfig,
  getAvatarVersion,
  subscribeAvatarConfig,
} from "../services/avatarConfig";
import type { StatusState } from "../types";

const LABELS: Record<StatusState, string> = {
  idle: "Pronta",
  thinking: "Pensando…",
  searching: "Buscando…",
  responding: "Respondendo…",
  listening: "Ouvindo…",
};

interface Expr {
  eyes: string;
  mouth: string;
  eyebrows: string;
}

const svgCache = new Map<string, string>();
function svgFor(base: Record<string, unknown>, e: Expr, version: number): string {
  const key = `${version}|${e.eyes}|${e.mouth}|${e.eyebrows}`;
  let svg = svgCache.get(key);
  if (svg === undefined) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    svg = createAvatar(avataaars, {
      ...base,
      eyes: [e.eyes],
      mouth: [e.mouth],
      eyebrows: [e.eyebrows],
    } as any).toString();
    svgCache.set(key, svg);
  }
  return svg;
}

function exprForStatus(status: StatusState): Expr {
  switch (status) {
    case "listening":
      return { eyes: "default", mouth: "twinkle", eyebrows: "raisedExcited" };
    case "thinking":
    case "searching":
      return { eyes: "side", mouth: "serious", eyebrows: "raisedExcited" };
    case "responding":
      return { eyes: "happy", mouth: "smile", eyebrows: "default" };
    default:
      return { eyes: "default", mouth: "smile", eyebrows: "default" };
  }
}

type Gesture = "none" | "blink" | "wink" | "tongue";

export function FriendlyAvatar({ status }: { status: StatusState }) {
  const [expr, setExpr] = useState<Expr>(() => exprForStatus("idle"));
  const statusRef = useRef(status);
  statusRef.current = status;
  const gestureRef = useRef<Gesture>("none");
  const mouthOpenRef = useRef(false);
  const lastMouthAt = useRef(0);

  // Gestos espontâneos: pisca com frequência; wink/língua de vez em quando (só
  // quando está paradinha), para não distrair durante o trabalho.
  useEffect(() => {
    let next = 0;
    let clear = 0;
    const schedule = () => {
      next = window.setTimeout(fire, 3500 + Math.random() * 5500);
    };
    const fire = () => {
      if (!audioPlayer.speaking) {
        const r = Math.random();
        let gesture: Gesture = "blink";
        let dur = 150;
        if (statusRef.current === "idle") {
          if (r > 0.9) {
            gesture = "tongue";
            dur = 850;
          } else if (r > 0.72) {
            gesture = "wink";
            dur = 450;
          }
        }
        gestureRef.current = gesture;
        clear = window.setTimeout(() => {
          gestureRef.current = "none";
        }, dur);
      }
      schedule();
    };
    schedule();
    return () => {
      clearTimeout(next);
      clearTimeout(clear);
    };
  }, []);

  // Loop principal: calcula a expressão-alvo a cada frame e só atualiza o React
  // quando ela muda (evita re-render à toa).
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const status = statusRef.current;
      const gesture = gestureRef.current;
      let target: Expr;

      if (audioPlayer.speaking) {
        // Lip-sync: abre/fecha a boca pela amplitude (com um mínimo de tempo
        // entre trocas para não tremer).
        const now = performance.now();
        if (now - lastMouthAt.current > 90) {
          mouthOpenRef.current = audioPlayer.amplitude() > 0.12;
          lastMouthAt.current = now;
        }
        target = {
          eyes: "happy",
          mouth: mouthOpenRef.current ? "default" : "twinkle",
          eyebrows: "default",
        };
      } else if (gesture === "blink") {
        target = { ...exprForStatus(status), eyes: "closed" };
      } else if (gesture === "wink") {
        target = { eyes: "wink", mouth: "twinkle", eyebrows: "default" };
      } else if (gesture === "tongue") {
        target = { eyes: "happy", mouth: "tongue", eyebrows: "default" };
      } else {
        target = exprForStatus(status);
      }

      setExpr((prev) =>
        prev.eyes === target.eyes &&
        prev.mouth === target.mouth &&
        prev.eyebrows === target.eyebrows
          ? prev
          : target,
      );
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  // Reage à personalização do usuário (config persistida).
  const version = useSyncExternalStore(subscribeAvatarConfig, getAvatarVersion);
  const base = useMemo(() => configToOptions(getAvatarConfig()), [version]);
  const svg = useMemo(() => svgFor(base, expr, version), [base, expr, version]);
  const speaking = audioPlayer.speaking;

  return (
    <div className={`favatar ${speaking ? "favatar--speaking" : ""}`}>
      <div className="favatar__glow" aria-hidden="true" />
      <div
        className="favatar__face"
        role="img"
        aria-label={`Friday — ${LABELS[status]}`}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      <div className="favatar__label">{LABELS[status]}</div>
    </div>
  );
}
