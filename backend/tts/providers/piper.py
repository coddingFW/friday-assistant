"""Adapter do Piper para a porta :class:`TTSProvider`.

Invoca o executável do Piper via subprocesso (assíncrono), passando o texto por
stdin e lendo o WAV gerado. É a única classe que conhece a linha de comando do
Piper; o resto do backend enxerga apenas a porta abstrata.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

from backend.tts.ports import SpeechAudio
from backend.utils.errors import TTSError, TTSUnavailableError
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class PiperTTSProvider:
    """Provedor de TTS que delega a síntese ao executável Piper local."""

    name = "piper"

    def __init__(self, *, binary: str, voice: str, timeout: float = 60.0) -> None:
        self._binary = self._resolve_binary(binary)
        self._voice = voice
        self._timeout = timeout

    @staticmethod
    def _resolve_binary(binary: str) -> str:
        """Resolve o executável do Piper de forma robusta (Windows-friendly).

        Ordem: caminho de arquivo existente → ao lado do interpretador atual
        (venv Scripts/bin, onde o pacote ``piper-tts`` instala) → PATH. Se nada
        resolver, mantém o valor original (erro claro no momento da síntese).
        """
        if os.path.isfile(binary):
            return os.path.abspath(binary)
        sibling = os.path.join(os.path.dirname(sys.executable), binary)
        for candidate in (sibling, f"{sibling}.exe"):
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(binary) or binary

    async def health(self) -> bool:
        """Retorna True se o modelo de voz está configurado e existe."""
        return bool(self._voice) and Path(self._voice).is_file()

    async def synthesize(self, text: str) -> SpeechAudio:
        """Sintetiza ``text`` em WAV usando o Piper."""
        content = text.strip()
        if not content:
            raise TTSError("Texto vazio para síntese.")
        if not self._voice:
            raise TTSUnavailableError(
                "Modelo de voz do Piper não configurado (FRIDAY_PIPER_VOICE)."
            )

        fd, out_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            audio = await self._run_piper(content, out_path)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(out_path)
        logger.info("piper_synth_ok", chars=len(content), bytes=len(audio))
        return SpeechAudio(data=audio, mime="audio/wav")

    async def _run_piper(self, text: str, out_path: str) -> bytes:
        """Executa o Piper e devolve os bytes do WAV gerado."""
        # O Piper é um programa Python; no Windows ele leria o stdin em cp1252,
        # corrompendo acentos (UTF-8 "é" -> "Ã©", lido como "A til"). Forçamos
        # modo UTF-8 no subprocesso para o texto chegar íntegro.
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            proc = await asyncio.create_subprocess_exec(
                self._binary,
                "-m",
                self._voice,
                "-f",
                out_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as exc:
            raise TTSUnavailableError(
                f"Executável Piper não encontrado: '{self._binary}'."
            ) from exc

        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(text.encode("utf-8")), timeout=self._timeout
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise TTSError("Síntese de voz excedeu o tempo limite.") from exc

        if proc.returncode != 0:
            detail = stderr.decode("utf-8", "replace")[:200]
            raise TTSError(f"Piper falhou (código {proc.returncode}): {detail}")

        return Path(out_path).read_bytes()
