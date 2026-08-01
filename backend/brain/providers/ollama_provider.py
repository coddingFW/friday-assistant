"""Adapter do Ollama para a porta :class:`LLMProvider`.

Fala com o serviço local do Ollama via HTTP (``/api/chat``, ``/api/tags``,
``/api/version``). É a única classe que conhece o formato de payload do Ollama;
o resto do backend enxerga apenas a porta abstrata.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from backend.brain.ports import ChatMessage
from backend.utils.errors import LLMError, LLMTimeoutError, LLMUnavailableError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class OllamaProvider:
    """Provedor de LLM que delega geração ao Ollama local."""

    name = "ollama"

    def __init__(self, client: httpx.AsyncClient, default_model: str) -> None:
        """Inicializa o adapter.

        Args:
            client: Cliente HTTP assíncrono já configurado com ``base_url`` e
                timeouts apontando para o serviço Ollama.
            default_model: Modelo usado quando a chamada não especifica outro.
        """
        self._client = client
        self._default_model = default_model

    async def health(self) -> bool:
        """Verifica se o Ollama responde em ``/api/version``."""
        try:
            response = await self._client.get("/api/version")
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("ollama_health_failed", error=str(exc))
            return False

    async def warmup(self, model: str | None = None) -> bool:
        """Pré-carrega o modelo na memória (elimina o cold start).

        Envia um ``/api/generate`` com prompt vazio: o Ollama carrega o modelo e
        retorna sem gerar texto. Falhas são tratadas como não-fatais.

        Returns:
            True se o modelo foi carregado; False em caso de falha.
        """
        target_model = model or self._default_model
        try:
            response = await self._client.post(
                "/api/generate",
                json={"model": target_model, "prompt": "", "stream": False},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("ollama_warmup_failed", model=target_model, error=str(exc))
            return False
        logger.info("ollama_warmup_ok", model=target_model)
        return True

    async def list_models(self) -> list[str]:
        """Lista os modelos instalados via ``/api/tags``."""
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMUnavailableError("Ollama inacessível.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha ao listar modelos: {exc}") from exc

        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Gera a resposta em streaming via ``/api/chat``.

        Consome o NDJSON do Ollama e emite apenas o conteúdo textual de cada
        fragmento. Traduz erros de rede/timeout para as exceções do domínio.
        """
        target_model = model or self._default_model
        payload = {
            "model": target_model,
            "messages": [self._to_ollama_message(m) for m in messages],
            "stream": True,
        }
        logger.info("ollama_stream_start", model=target_model, messages=len(messages))

        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise LLMError(
                        f"Ollama retornou {resp.status_code}: {body[:200]}"
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = self._parse_line(line)
                    if chunk is None:
                        continue
                    content, done = chunk
                    if content:
                        yield content
                    if done:
                        break
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                "Ollama inacessível — o serviço está em execução?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Tempo limite excedido ao gerar resposta.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha de comunicação com o Ollama: {exc}") from exc

        logger.info("ollama_stream_end", model=target_model)

    @staticmethod
    def _to_ollama_message(message: ChatMessage) -> dict[str, object]:
        """Converte uma ChatMessage para o formato de mensagem do Ollama.

        Inclui ``images`` (base64) apenas quando presentes, mantendo o payload
        de conversas somente-texto idêntico ao anterior.
        """
        payload: dict[str, object] = {
            "role": message.role,
            "content": message.content,
        }
        if message.images:
            payload["images"] = list(message.images)
        return payload

    @staticmethod
    def _parse_line(line: str) -> tuple[str, bool] | None:
        """Decodifica uma linha NDJSON do Ollama.

        Returns:
            Tupla ``(conteúdo, concluído)`` ou ``None`` se a linha for inválida.
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("ollama_bad_json_line", line=line[:120])
            return None
        content = data.get("message", {}).get("content", "")
        return content, bool(data.get("done", False))
