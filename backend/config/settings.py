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
            "Você é Friday, uma assistente local, direta e prestativa. Responda "
            "sempre em português do Brasil, de forma clara. Atenda exatamente ao "
            "que for pedido: se pedirem código, entregue código completo e "
            "funcional, sem se recusar nem responder de forma genérica. "
            "Um contexto de busca pode (ou não) ser fornecido: use-o apenas "
            "quando for realmente relevante para a pergunta e, nesse caso, cite "
            "as fontes que usar. Se o contexto não ajudar, ou se a pergunta não "
            "depender de informação da web (por exemplo, pedidos de código, "
            "tarefas criativas ou conhecimento geral), ignore-o e responda com "
            "seu próprio conhecimento — sem mencionar que não encontrou fontes."
        ),
        description="Prompt de sistema base da assistente.",
    )

    # --- Conversa (memória de curto prazo) --------------------------------
    history_max_messages: int = Field(
        default=12,
        ge=0,
        description=(
            "Máximo de mensagens (user+assistant) de histórico mantidas por "
            "conexão para dar contexto multi-turno ao LLM. 0 desativa a memória "
            "de conversa; a memória de longo prazo (persistente) é a Fase 9."
        ),
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
    tts_fillers_enabled: bool = Field(
        default=True,
        description=(
            "Se True, a Friday fala uma frase-ponte curta enquanto busca (RAG), "
            "para não ficar em silêncio — conversa mais natural."
        ),
    )
    tts_filler_phrases: list[str] = Field(
        default_factory=lambda: [
            "Deixa eu ver isso.",
            "Só um instante.",
            "Deixa eu procurar aqui.",
            "Um momento, já respondo.",
        ],
        description="Frases-ponte faladas durante a busca (escolhidas ao acaso).",
    )

    # --- STT (transcrição de voz — Fase 6) --------------------------------
    stt_enabled: bool = Field(
        default=True,
        description=(
            "Se True, registra o microfone e habilita a transcrição de voz "
            "(Whisper). Desligue para não carregar o motor de STT."
        ),
    )
    stt_provider: str = Field(
        default="whisper", description="Provedor de STT (Strategy). Atual: whisper."
    )
    whisper_model: str = Field(
        default="small",
        description=(
            "Modelo Whisper (tiny|base|small|medium|large-v3). 'small' equilibra "
            "qualidade e CPU para PT-BR; baixado do HuggingFace na 1ª vez."
        ),
    )
    whisper_device: str = Field(
        default="cpu", description="Dispositivo do Whisper: cpu | cuda."
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="Precisão do CTranslate2 (int8|int8_float16|float16|float32).",
    )
    whisper_language: str = Field(
        default="pt",
        description="Idioma assumido na transcrição ('' = detecção automática).",
    )
    whisper_beam_size: int = Field(
        default=1, ge=1, le=10, description="Beam search (1 = mais rápido/greedy)."
    )

    # --- Microfone (endpointing por energia) ------------------------------
    mic_sample_rate: int = Field(
        default=16000, ge=8000, le=48000, description="Taxa de captura (Hz)."
    )
    mic_frame_ms: int = Field(
        default=30, ge=10, le=60, description="Duração de cada frame de análise (ms)."
    )
    mic_silence_ms: int = Field(
        default=800,
        ge=100,
        description="Silêncio (ms) após fala que encerra a utterance (endpoint).",
    )
    mic_energy_threshold: float = Field(
        default=500.0,
        ge=0,
        description="Limiar de RMS (escala int16) acima do qual há fala.",
    )
    mic_min_speech_ms: int = Field(
        default=300,
        ge=0,
        description="Fala mínima (ms) para valer como utterance (filtra ruídos).",
    )
    mic_max_utterance_ms: int = Field(
        default=15000, ge=1000, description="Duração máxima de uma utterance (ms)."
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
