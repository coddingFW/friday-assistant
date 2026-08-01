"""Portas (interfaces) da camada de LLM — Ports & Adapters.

O domínio depende apenas destas abstrações, nunca de um provedor concreto.
Qualquer provedor (Ollama hoje; llama.cpp, vLLM etc. no futuro) é um *adapter*
que implementa :class:`LLMProvider`. Isso concretiza o Strategy Pattern exigido
pela arquitetura: a troca de provedor é uma decisão de configuração.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Uma mensagem de conversa, agnóstica de provedor.

    Preparada para multimodalidade: ``images`` carrega anexos visuais já
    codificados em base64, consumidos por modelos de visão locais (ex.: llava
    via Ollama). Vazio por padrão — o fluxo somente-texto permanece inalterado.
    """

    role: Role
    content: str
    images: tuple[str, ...] = ()


@runtime_checkable
class LLMProvider(Protocol):
    """Contrato que todo provedor de LLM deve cumprir.

    Implementações devem ser assíncronas, respeitar timeouts e traduzir falhas
    de infraestrutura para as exceções de :mod:`backend.utils.errors`.
    """

    #: Identificador curto do provedor (ex.: ``"ollama"``).
    name: str

    async def health(self) -> bool:
        """Retorna True se o serviço está acessível e pronto."""
        ...

    async def list_models(self) -> list[str]:
        """Lista os modelos disponíveis no provedor."""
        ...

    def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Gera a resposta em streaming, token a token.

        Args:
            messages: Histórico da conversa em ordem cronológica.
            model: Sobrescreve o modelo default apenas para esta chamada.

        Yields:
            Fragmentos de texto (tokens) à medida que são gerados.

        Raises:
            LLMUnavailableError: Serviço inacessível.
            LLMTimeoutError: Tempo limite excedido.
            LLMError: Demais falhas do provedor.
        """
        ...
