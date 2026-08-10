// Painel de personalização do avatar. Mostra todas as peças do Avataaars (locais,
// offline) como miniaturas e swatches; a escolha é salva na hora (avatarConfig).

import type { ReactNode } from "react";
import { useSyncExternalStore } from "react";
import { createAvatar } from "@dicebear/core";
import { avataaars } from "@dicebear/collection";
import {
  OPTIONS,
  configToOptions,
  getAvatarConfig,
  getAvatarVersion,
  resetAvatarConfig,
  setAvatarConfig,
  subscribeAvatarConfig,
} from "../services/avatarConfig";
import type { AvatarConfig } from "../services/avatarConfig";

// Base neutra só para as MINIATURAS (mostra o formato da peça, não as cores atuais).
const THUMB_BASE: Record<string, unknown> = {
  seed: "friday",
  backgroundColor: ["transparent"],
  skinColor: ["edb98a"],
  hairColor: ["724133"],
  clothesColor: ["65c9ff"],
  eyes: ["default"],
  mouth: ["smile"],
  eyebrows: ["default"],
  top: ["shortWaved"],
  topProbability: 100,
  clothing: ["shirtCrewNeck"],
  facialHairProbability: 0,
  accessoriesProbability: 0,
};

type PartKind = "top" | "clothing" | "accessories" | "facialHair";
const thumbCache = new Map<string, string>();

function partThumb(kind: PartKind, value: string | null): string {
  const key = `${kind}|${value}`;
  const cached = thumbCache.get(key);
  if (cached) return cached;
  const opts: Record<string, unknown> = { ...THUMB_BASE };
  if (kind === "top" && value) opts.top = [value];
  if (kind === "clothing" && value) opts.clothing = [value];
  if (kind === "accessories" && value) {
    opts.accessories = [value];
    opts.accessoriesProbability = 100;
  }
  if (kind === "facialHair" && value) {
    opts.facialHair = [value];
    opts.facialHairProbability = 100;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const svg = createAvatar(avataaars, opts as any).toString();
  thumbCache.set(key, svg);
  return svg;
}

function previewSvg(config: AvatarConfig): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return createAvatar(avataaars, {
    ...configToOptions(config),
    eyes: ["default"],
    mouth: ["smile"],
    eyebrows: ["default"],
  } as any).toString();
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="cz-section">
      <h3 className="cz-section__title">{title}</h3>
      {children}
    </div>
  );
}

function ThumbRow({
  kind,
  values,
  selected,
  onPick,
}: {
  kind: PartKind;
  values: readonly (string | null)[];
  selected: string | null;
  onPick: (v: string | null) => void;
}) {
  return (
    <div className="cz-row">
      {values.map((v) => (
        <button
          key={String(v)}
          type="button"
          className={`cz-thumb ${v === selected ? "cz-thumb--on" : ""}`}
          title={v ?? "Nenhum"}
          onClick={() => onPick(v)}
          dangerouslySetInnerHTML={{ __html: partThumb(kind, v) }}
        />
      ))}
    </div>
  );
}

function Swatches({
  values,
  selected,
  onPick,
}: {
  values: readonly string[];
  selected: string;
  onPick: (v: string) => void;
}) {
  return (
    <div className="cz-row cz-row--swatch">
      {values.map((v) => (
        <button
          key={v}
          type="button"
          className={`cz-swatch ${v === selected ? "cz-swatch--on" : ""} ${
            v === "transparent" ? "cz-swatch--none" : ""
          }`}
          title={v}
          style={v === "transparent" ? undefined : { background: `#${v}` }}
          onClick={() => onPick(v)}
        />
      ))}
    </div>
  );
}

export function AvatarCustomizer({ open, onClose }: { open: boolean; onClose: () => void }) {
  // Re-renderiza quando a config muda (destaque do selecionado + preview).
  useSyncExternalStore(subscribeAvatarConfig, getAvatarVersion);
  const config = getAvatarConfig();
  if (!open) return null;

  return (
    <div className="cz-overlay" onClick={onClose}>
      <div className="cz-panel" onClick={(e) => e.stopPropagation()}>
        <header className="cz-head">
          <h2>Personalizar avatar</h2>
          <button type="button" className="cz-x" onClick={onClose} title="Fechar">
            ✕
          </button>
        </header>

        <div className="cz-preview">
          <div dangerouslySetInnerHTML={{ __html: previewSvg(config) }} />
        </div>

        <div className="cz-controls">
          <Section title="Cabelo / chapéu">
            <ThumbRow kind="top" values={OPTIONS.top} selected={config.top} onPick={(v) => setAvatarConfig({ top: v ?? "shortWaved" })} />
          </Section>
          <Section title="Cor do cabelo">
            <Swatches values={OPTIONS.hairColor} selected={config.hairColor} onPick={(v) => setAvatarConfig({ hairColor: v })} />
          </Section>
          <Section title="Tom de pele">
            <Swatches values={OPTIONS.skinColor} selected={config.skinColor} onPick={(v) => setAvatarConfig({ skinColor: v })} />
          </Section>
          <Section title="Roupa">
            <ThumbRow kind="clothing" values={OPTIONS.clothing} selected={config.clothing} onPick={(v) => setAvatarConfig({ clothing: v ?? "shirtCrewNeck" })} />
          </Section>
          <Section title="Cor da roupa">
            <Swatches values={OPTIONS.clothesColor} selected={config.clothesColor} onPick={(v) => setAvatarConfig({ clothesColor: v })} />
          </Section>
          <Section title="Óculos / acessórios">
            <ThumbRow kind="accessories" values={[null, ...OPTIONS.accessories]} selected={config.accessories} onPick={(v) => setAvatarConfig({ accessories: v })} />
          </Section>
          <Section title="Barba">
            <ThumbRow kind="facialHair" values={[null, ...OPTIONS.facialHair]} selected={config.facialHair} onPick={(v) => setAvatarConfig({ facialHair: v })} />
          </Section>
          <Section title="Fundo">
            <Swatches values={["transparent", "34d6c0", "0e151e", "ff488e", "65c9ff", "f8d25c"]} selected={config.background} onPick={(v) => setAvatarConfig({ background: v })} />
          </Section>
        </div>

        <footer className="cz-foot">
          <button type="button" className="cz-reset" onClick={resetAvatarConfig}>
            Restaurar padrão
          </button>
          <button type="button" className="cz-done" onClick={onClose}>
            Concluído
          </button>
        </footer>
      </div>
    </div>
  );
}
