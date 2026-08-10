"""Normalização de texto para síntese de voz.

A resposta do LLM costuma conter markdown, símbolos, URLs e marcadores de citação
(``[1]``, ``(Fonte: ...)``) que o TTS lê literalmente ("asterisco", "colchete").
Esta função limpa o texto **apenas para a fala** — o texto exibido ao usuário
permanece com a formatação original.

Blocos de código são o pior caso: sem tratamento, o TTS leria cada tag, símbolo
e linha em voz alta. Por isso eles são removidos e substituídos por uma pista
curta (:data:`_CODE_PLACEHOLDER`); o código continua visível na tela.
"""

from __future__ import annotations

import re

# Bloco de código cercado (```lang ... ```). Também casa um bloco não terminado
# (modelo cortado no meio) até o fim do texto, para nada de código vazar na fala.
_CODE_FENCE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_CODE_PLACEHOLDER = " Código exibido na tela. "

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
    # Blocos de código primeiro: antes de _EMPHASIS remover as crases da cerca.
    t = _CODE_FENCE.sub(_CODE_PLACEHOLDER, text)
    t = _MD_LINK.sub(r"\1", t)
    t = _URL.sub("", t)
    t = _SOURCE_PAREN.sub("", t)   # remove "(Fonte: ...)" inteiro
    t = _CITATION.sub("", t)       # remove marcadores [n]
    t = _LIST_PREFIX.sub("", t)
    t = _EMPHASIS.sub("", t)
    t = _OTHER_SYMBOLS.sub(" ", t)  # parênteses, colchetes, barras, etc.
    t = _MULTI_PUNCT.sub(r"\1", t)  # remove espaço antes de pontuação
    t = _WS.sub(" ", t).strip()
    return t
