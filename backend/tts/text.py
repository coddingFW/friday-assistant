"""Normalização de texto para síntese de voz.

A resposta do LLM costuma conter markdown, símbolos, URLs e marcadores de citação
(``[1]``, ``(Fonte: ...)``) que o TTS lê literalmente ("asterisco", "colchete").
Esta função limpa o texto **apenas para a fala** — o texto exibido ao usuário
permanece com a formatação original.
"""

from __future__ import annotations

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")          # [rótulo](url) -> rótulo
_URL = re.compile(r"https?://\S+")                        # URLs soltas
_SOURCE_PAREN = re.compile(r"\(\s*fontes?\s*:.*?\)", re.IGNORECASE | re.DOTALL)
_CITATION = re.compile(r"\[\s*\d+\s*\]")                  # [1], [ 2 ]
_LIST_PREFIX = re.compile(r"(?m)^\s*[-*+]\s+")            # marcadores de lista
_EMPHASIS = re.compile(r"[*_`~#>|]+")                     # markdown/símbolos
_OTHER_SYMBOLS = re.compile(r"[^\w\s.,!?;:'\-]", re.UNICODE)  # demais símbolos -> espaço
_MULTI_PUNCT = re.compile(r"\s+([.,!?;:])")
_WS = re.compile(r"\s+")


def to_speech_text(text: str) -> str:
    """Converte texto (possivelmente com markdown) em texto limpo para fala."""
    t = _MD_LINK.sub(r"\1", text)
    t = _URL.sub("", t)
    t = _SOURCE_PAREN.sub("", t)   # remove "(Fonte: ...)" inteiro
    t = _CITATION.sub("", t)       # remove marcadores [n]
    t = _LIST_PREFIX.sub("", t)
    t = _EMPHASIS.sub("", t)
    t = _OTHER_SYMBOLS.sub(" ", t)  # parênteses, colchetes, barras, etc.
    t = _MULTI_PUNCT.sub(r"\1", t)  # remove espaço antes de pontuação
    t = _WS.sub(" ", t).strip()
    return t
