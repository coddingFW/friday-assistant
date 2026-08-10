// Configuração persistente do avatar da Friday (partes fixas: cabelo, roupa,
// cores, acessórios…). As expressões dinâmicas (olhos/boca por estado) NÃO ficam
// aqui — só o "visual base". Salvo em localStorage para personalizar quando quiser.

export interface AvatarConfig {
  top: string;
  hairColor: string;
  skinColor: string;
  clothing: string;
  clothesColor: string;
  accessories: string | null; // null = nenhum
  facialHair: string | null; // null = nenhuma
  facialHairColor: string;
  background: string; // "transparent" ou hex (sem #)
}

export const DEFAULT_CONFIG: AvatarConfig = {
  top: "shortWaved",
  hairColor: "b58143",
  skinColor: "57331f",
  clothing: "shirtCrewNeck",
  clothesColor: "ff4c77",
  accessories: null,
  facialHair: null,
  facialHairColor: "2c1b18",
  background: "transparent",
};

// Catálogo de opções (todos os itens que vêm com o DiceBear/Avataaars, offline).
export const OPTIONS = {
  top: [
    "shortWaved", "shortFlat", "shortRound", "shortCurly", "theCaesar",
    "theCaesarAndSidePart", "sides", "shavedSides", "frizzle", "shaggy",
    "shaggyMullet", "bigHair", "bob", "bun", "curly", "curvy", "dreads",
    "dreads01", "dreads02", "frida", "fro", "froBand", "longButNotTooLong",
    "miaWallace", "straight01", "straight02", "straightAndStrand",
    "hat", "hijab", "turban", "winterHat1", "winterHat02", "winterHat03", "winterHat04",
  ],
  clothing: [
    "shirtCrewNeck", "shirtScoopNeck", "shirtVNeck", "hoodie", "collarAndSweater",
    "blazerAndShirt", "blazerAndSweater", "graphicShirt", "overall",
  ],
  accessories: ["prescription01", "prescription02", "round", "wayfarers", "sunglasses", "kurt", "eyepatch"],
  facialHair: ["beardLight", "beardMedium", "beardMajestic", "moustacheFancy", "moustacheMagnum"],
  skinColor: ["57331f", "614335", "ae5d29", "d08b5b", "fd9841", "edb98a", "ffdbb4", "f8d25c"],
  hairColor: ["b58143", "2c1b18", "a55728", "724133", "4a312c", "d6b370", "c93305", "f59797", "ecdcbf", "e8e1e1"],
  clothesColor: ["ff4c77", "ff488e", "ff5c5c", "ffafb9", "65c9ff", "5199e4", "25557c", "a7ffc4", "b1e2ff", "929598", "3c4f5c", "262e33", "e6e6e6", "ffffff"],
} as const;

const KEY = "friday.avatar";

function load(): AvatarConfig {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...DEFAULT_CONFIG, ...JSON.parse(raw) } : { ...DEFAULT_CONFIG };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

let current: AvatarConfig = load();
let version = 0;
const listeners = new Set<() => void>();

export function getAvatarConfig(): AvatarConfig {
  return current;
}
export function getAvatarVersion(): number {
  return version;
}
export function setAvatarConfig(patch: Partial<AvatarConfig>): void {
  current = { ...current, ...patch };
  version++;
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    /* storage opcional */
  }
  listeners.forEach((fn) => fn());
}
export function resetAvatarConfig(): void {
  current = { ...DEFAULT_CONFIG };
  version++;
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  listeners.forEach((fn) => fn());
}
export function subscribeAvatarConfig(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

// Converte a config nas opções que o DiceBear/avataaars espera.
export function configToOptions(c: AvatarConfig): Record<string, unknown> {
  return {
    seed: "friday",
    backgroundColor: [c.background],
    skinColor: [c.skinColor],
    hairColor: [c.hairColor],
    top: [c.top],
    topProbability: 100,
    clothing: [c.clothing],
    clothesColor: [c.clothesColor],
    accessories: c.accessories ? [c.accessories] : [],
    accessoriesProbability: c.accessories ? 100 : 0,
    facialHair: c.facialHair ? [c.facialHair] : [],
    facialHairProbability: c.facialHair ? 100 : 0,
    facialHairColor: [c.facialHairColor],
  };
}
