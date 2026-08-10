// Detecção da palavra de ativação ("wake word") na transcrição do Whisper.
// Tolerante à grafia: o Whisper pode escrever "Friday" de várias formas em PT-BR.

function normalizeWord(w: string): string {
  return w
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // remove acentos
    .replace(/[^\w]/g, ""); // remove pontuação
}

// Grafias que o Whisper costuma gerar para "Friday" em português.
const FRIDAY_VARIANTS = [
  "friday", "fraidei", "fraidi", "fraide", "fride", "fraidey", "fraiday", "sexta",
];

export function wakeVariants(wakeWord: string): Set<string> {
  const w = normalizeWord(wakeWord);
  if (w === "friday" || w === "sexta") return new Set(FRIDAY_VARIANTS);
  return new Set([w]);
}

/**
 * Procura a wake word entre as primeiras palavras da fala. Se achar, devolve o
 * comando (o texto ORIGINAL após a palavra, preservando acentos/maiúsculas).
 */
export function detectWake(
  text: string,
  wakeWord: string,
): { matched: boolean; command: string } {
  const words = text.split(/\s+/).filter(Boolean);
  const variants = wakeVariants(wakeWord);
  const limit = Math.min(words.length, 4); // a wake word deve vir no começo
  for (let i = 0; i < limit; i++) {
    if (variants.has(normalizeWord(words[i]))) {
      const command = words
        .slice(i + 1)
        .join(" ")
        .replace(/^[\s,.:;!?…-]+/, "")
        .trim();
      return { matched: true, command };
    }
  }
  return { matched: false, command: "" };
}
