"""Hierarquia central de exceções do domínio.

Toda falha previsível do backend deve ser expressa por uma destas exceções,
nunca por exceções genéricas vazando das camadas de infraestrutura. Isso mantém
a camada de API desacoplada dos detalhes de cada serviço externo (Ollama etc.).
"""

from __future__ import annotations


class FridayError(Exception):
    """Exceção base de toda a aplicação Friday."""


class LLMError(FridayError):
    """Falha genérica na camada de LLM."""


class LLMUnavailableError(LLMError):
    """O serviço de LLM (ex.: Ollama) está inacessível ou não respondeu.

    Normalmente indica que o serviço local não está em execução.
    """


class LLMTimeoutError(LLMError):
    """A geração excedeu o tempo limite configurado."""


class ProviderConfigError(FridayError):
    """Configuração inválida ao selecionar a estratégia de provedor."""


class RagError(FridayError):
    """Falha genérica na camada de RAG (busca/contexto)."""


class SearchUnavailableError(RagError):
    """O provedor de busca web está inacessível ou falhou."""


class SensorError(FridayError):
    """Falha genérica na camada de sensores (percepção multimodal)."""


class SensorNotFoundError(SensorError):
    """Nenhum sensor registrado corresponde ao identificador solicitado."""
