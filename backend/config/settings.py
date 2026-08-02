"""Configuração central da aplicação.

Fonte única de verdade para todos os parâmetros do backend. Os valores são
carregados nesta ordem de precedência (maior primeiro):

1. Variáveis de ambiente com prefixo ``FRIDAY_`` (ex.: ``FRIDAY_LLM_MODEL``).
2. Arquivo ``.env`` na raiz de execução.
3. Defaults definidos aqui.

Trocar de modelo ou de provedor de LLM é, por decisão arquitetural (ADR-0002),
uma alteração *apenas de configuração* — nenhum código do domínio precisa mudar.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parâmetros de configuração validados da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FRIDAY_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicação ---------------------------------------------------------
    app_name: str = Field(default="Friday", description="Nome da assistente.")
    environment: str = Field(
        default="development",
        description="Ambiente de execução: development | production.",
    )
    log_level: str = Field(default="INFO", description="Nível de log raiz.")
    log_json: bool = Field(
        default=False,
        description="Se True, emite logs em JSON (produção); senão, console legível.",
    )

    # --- Servidor HTTP/WebSocket -------------------------------------------
    host: str = Field(
        default="127.0.0.1",
        description="Bind do servidor. 127.0.0.1 = só local; 0.0.0.0 exporia na LAN.",
    )
    port: int = Field(default=8000, ge=1, le=65535, description="Porta do backend.")
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:1420",  # Vite/Tauri dev
            "http://127.0.0.1:1420",
            "tauri://localhost",       # app Tauri empacotado
        ],
        description="Origens permitidas para o cliente (frontend desacoplado).",
    )

    # --- LLM (Strategy Pattern) -------------------------------------------
    llm_provider: str = Field(
        default="ollama",
        description="Provedor de LLM ativo. Estratégia selecionada em brain/factory.py.",
    )
    llm_model: str = Field(
        default="llama3.1:8b",
        description="Modelo default. Trocável via config (ex.: qwen3, mistral, gemma).",
    )

    # --- RAG (busca web + contexto) ---------------------------------------
    rag_enabled: bool = Field(
        default=True,
        description="Se True, enriquece as respostas com busca web (RAG).",
    )
    rag_provider: str = Field(
        default="duckduckgo",
        description="Provedor de busca (Strategy). Atual: duckduckgo.",
    )
    rag_max_results: int = Field(
        default=3, ge=1, le=10, description="Nº de resultados recuperados (top-N)."
    )
    rag_region: str = Field(
        default="wt-wt", description="Região da busca DuckDuckGo (wt-wt = global)."
    )
    rag_timeout: float = Field(
        default=20.0,
        gt=0,
        description=(
            "Timeout (s) da busca web. A ddgs agrega múltiplos motores; um valor "
            "muito baixo corta motores lentos e retorna menos/nenhuma fonte."
        ),
    )
    rag_system_prompt: str = Field(
        default=(
            "Você é Friday, uma assistente local e prestativa. Responda em "
            "português do Brasil, de forma clara e concisa. Quando um contexto de "
            "busca for fornecido, use-o para embasar a resposta e cite as fontes "
            "relevantes; se o contexto não ajudar, responda com seu próprio "
            "conhecimento e diga que não encontrou fontes recentes."
        ),
        description="Prompt de sistema base da assistente.",
    )

    # --- TTS (síntese de voz) ---------------------------------------------
    tts_enabled: bool = Field(
        default=False,
        description="Se True, sintetiza voz da resposta (Piper) e envia ao cliente.",
    )
    tts_provider: str = Field(
        default="piper", description="Provedor de TTS (Strategy). Atual: piper."
    )
    piper_binary: str = Field(
        default="piper",
        description="Caminho do executável Piper (no PATH ou absoluto).",
    )
    piper_voice: str = Field(
        default="",
        description="Caminho do modelo de voz .onnx PT-BR (vazio = não configurado).",
    )
    tts_timeout: float = Field(
        default=60.0, gt=0, description="Timeout (s) da síntese de voz."
    )

    # --- Ollama (serviço local) -------------------------------------------
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="URL base do serviço Ollama local.",
    )
    ollama_connect_timeout: float = Field(
        default=5.0, gt=0, description="Timeout (s) para conectar ao Ollama."
    )
    ollama_read_timeout: float = Field(
        default=300.0,
        gt=0,
        description=(
            "Timeout (s) de leitura por chunk durante streaming. Default alto "
            "para acomodar cold start + prefill de prompts grandes (RAG) em CPU."
        ),
    )
    ollama_warmup: bool = Field(
        default=False,
        description=(
            "Se True, pré-carrega o modelo no startup (em segundo plano) para "
            "eliminar o cold start na primeira interação. Falhas são ignoradas."
        ),
    )

    @property
    def is_production(self) -> bool:
        """Retorna True em ambiente de produção."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única (cacheada) de configuração.

    Usar via ``Depends(get_settings)`` no FastAPI para injeção de dependência.
    O cache garante uma única leitura de ambiente por processo.
    """
    return Settings()
