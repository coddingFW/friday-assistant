"""Adapter do Ollama para a porta :class:`LLMProvider`.

Fala com o serviço local do Ollama via HTTP (``/api/chat``, ``/api/tags``,
``/api/version``). É a única classe que conhece o formato de payload do Ollama;
o resto do backend enxerga apenas a porta abstrata.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from backend.brain.ports import ChatMessage, GenerationOptions
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

    async def warmup(
        self, model: str | None = None, options: GenerationOptions | None = None
    ) -> bool:
        """Pré-carrega o modelo na memória (elimina o cold start).

        Envia um ``/api/generate`` com prompt vazio: o Ollama carrega o modelo e
        retorna sem gerar texto. Falhas são tratadas como não-fatais. Passe as
        mesmas ``options`` dos turnos: o Ollama recarrega o modelo quando o
        ``num_ctx`` muda, o que desperdiçaria o warm-up.

        Returns:
            True se o modelo foi carregado; False em caso de falha.
        """
        target_model = model or self._default_model
        payload: dict[str, object] = {
            "model": target_model,
            "prompt": "",
            "stream": False,
        }
        ollama_options = self._to_ollama_options(options)
        if ollama_options:
            payload["options"] = ollama_options
        try:
            response = await self._client.post("/api/generate", json=payload)
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
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[str]:
        """Gera a resposta em streaming via ``/api/chat``.

        Consome o NDJSON do Ollama e emite apenas o conteúdo textual de cada
        fragmento. Traduz erros de rede/timeout para as exceções do domínio.
        Ao fim, registra quantos tokens o prompt ocupou e avisa quando chegou
        perto de ``num_ctx`` (sinal de que o Ollama pode ter truncado o prompt).
        """
        target_model = model or self._default_model
        payload: dict[str, object] = {
            "model": target_model,
            "messages": [self._to_ollama_message(m) for m in messages],
            "stream": True,
        }
        ollama_options = self._to_ollama_options(options)
        if ollama_options:
            payload["options"] = ollama_options
        num_ctx = options.num_ctx if options else None
        logger.info(
            "ollama_stream_start",
            model=target_model,
            messages=len(messages),
            num_ctx=num_ctx,
        )

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
                    content, done, data = chunk
                    if content:
                        yield content
                    if done:
                        self._log_usage(target_model, data, num_ctx)
                        break
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                "Ollama inacessível — o serviço está em execução?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Tempo limite excedido ao gerar resposta.") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha de comunicação com o Ollama: {exc}") from exc

    @staticmethod
    def _to_ollama_options(options: GenerationOptions | None) -> dict[str, object]:
        """Traduz :class:`GenerationOptions` para o ``options`` do Ollama (só o definido)."""
        if options is None:
            return {}
        result: dict[str, object] = {}
        if options.num_ctx is not None:
            result["num_ctx"] = options.num_ctx
        if options.temperature is not None:
            result["temperature"] = options.temperature
        return result

    @staticmethod
    def _log_usage(model: str, data: dict[str, object], num_ctx: int | None) -> None:
        """Loga o uso de tokens do turno e avisa se o prompt encostou no limite."""
        prompt_tokens = data.get("prompt_eval_count")
        logger.info(
            "ollama_stream_end",
            model=model,
            prompt_tokens=prompt_tokens,
            output_tokens=data.get("eval_count"),
            num_ctx=num_ctx,
        )
        if (
            isinstance(prompt_tokens, int)
            and num_ctx
            and prompt_tokens >= int(num_ctx * 0.9)
        ):
            logger.warning(
                "ollama_context_near_limit",
                model=model,
                prompt_tokens=prompt_tokens,
                num_ctx=num_ctx,
                hint="Aumente FRIDAY_CODE_NUM_CTX/FRIDAY_LLM_NUM_CTX ou reduza o contexto.",
            )

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
    def _parse_line(line: str) -> tuple[str, bool, dict[str, object]] | None:
        """Decodifica uma linha NDJSON do Ollama.

        Returns:
            Tupla ``(conteúdo, concluído, dados brutos)`` ou ``None`` se a linha
            for inválida. Os dados brutos trazem as métricas do chunk final.
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("ollama_bad_json_line", line=line[:120])
            return None
        content = data.get("message", {}).get("content", "")
        return content, bool(data.get("done", False)), data
