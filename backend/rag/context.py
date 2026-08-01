"""Construção do bloco de contexto textual a partir dos resultados de busca."""

from __future__ import annotations

from backend.rag.ports import SearchResult


def build_context(results: list[SearchResult]) -> str:
    """Formata os resultados em um contexto legível para o LLM.

    Args:
        results: Resultados de busca (já limitados ao top-N).

    Returns:
        Bloco de texto numerado com título, URL e trecho de cada fonte. String
        vazia se não houver resultados.
    """
    if not results:
        return ""

    linhas = ["Contexto de busca (fontes recentes):", ""]
    for i, r in enumerate(results, start=1):
        linhas.append(f"[{i}] {r.title}")
        linhas.append(f"    Fonte: {r.url}")
        if r.snippet:
            linhas.append(f"    Trecho: {r.snippet}")
        linhas.append("")
    return "\n".join(linhas).strip()
