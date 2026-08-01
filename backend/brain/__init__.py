"""Camada de orquestração cognitiva (o "cérebro").

Na Fase 1 expõe apenas a abstração de provedor de LLM (porta) e a estratégia
de seleção. A orquestração de conversa completa (RAG, memória) entra nas fases
seguintes, sempre falando com o LLM exclusivamente através da porta definida aqui.
"""

from backend.brain.factory import create_llm_provider
from backend.brain.ports import ChatMessage, LLMProvider

__all__ = ["create_llm_provider", "ChatMessage", "LLMProvider"]
