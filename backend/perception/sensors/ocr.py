"""Sensor de OCR — ``OnDemandSensor`` (Fase 8, visão).

Extrai o **texto literal** de uma imagem (upload do cliente ou captura de tela)
via Tesseract (``pytesseract`` + ``Pillow``), sem depender do LLM de visão: o
LLM *interpreta* a imagem; o OCR *transcreve* o que está escrito nela.

O reconhecimento é bloqueante, então roda num worker thread. O motor é injetável
para permitir testes sem o binário do Tesseract instalado. Sem o Tesseract, o
sensor degrada com :class:`OcrUnavailableError` (mensagem orientando a instalação),
tal como o modelo de visão pede ``ollama pull llava``.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from backend.perception.modality import Modality, Percept
from backend.perception.ports import SensorDescriptor, SensorKind
from backend.utils.errors import OcrUnavailableError, SensorError
from backend.utils.logging import get_logger

logger = get_logger(__name__)

#: Motor de OCR: recebe (bytes da imagem, idioma) e devolve o texto extraído.
OcrEngine = Callable[[bytes, str], str]

OCR_DESCRIPTOR = SensorDescriptor(
    id="ocr",
    modality=Modality.OCR_TEXT,
    kind=SensorKind.ON_DEMAND,
    name="OCR",
    description="Extrai o texto literal de uma imagem (Tesseract), 100% local.",
)


def _default_engine(tesseract_cmd: str, tessdata_dir: str = "") -> OcrEngine:
    """Cria o motor padrão (pytesseract + Pillow) com o caminho opcional do binário.

    ``tessdata_dir``, se informado, é passado como ``--tessdata-dir`` — permite usar
    um diretório de idiomas gravável quando não se pode escrever no ``tessdata`` da
    instalação (caso comum no Windows, sob Program Files).
    """

    def _run(data: bytes, lang: str) -> str:
        try:
            import io
            import os

            import pytesseract
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - ambiente sem deps
            raise OcrUnavailableError(
                "OCR indisponível: instale as dependências com "
                "'pip install pytesseract Pillow'."
            ) from exc

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        # TESSDATA_PREFIX é lido nativamente pelo Tesseract e não sofre com o split
        # ingênuo (por espaços) que o pytesseract aplica ao 'config' — logo, seguro
        # para caminhos com espaços (ex.: Program Files).
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir

        try:
            with Image.open(io.BytesIO(data)) as img:
                return pytesseract.image_to_string(img, lang=lang)
        except pytesseract.TesseractNotFoundError as exc:
            raise OcrUnavailableError(
                "Tesseract não encontrado. Instale-o (Windows: "
                "https://github.com/UB-Mannheim/tesseract/wiki) e, se não estiver "
                "no PATH, aponte o caminho em FRIDAY_OCR_TESSERACT_CMD."
            ) from exc
        except OSError as exc:  # imagem inválida/corrompida
            raise SensorError(f"Imagem inválida para OCR: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - traduz falha do Tesseract
            raise SensorError(f"Falha no OCR: {exc}") from exc

    return _run


class OcrSensor:
    """``OnDemandSensor`` que transcreve o texto de uma imagem via Tesseract."""

    descriptor = OCR_DESCRIPTOR

    def __init__(
        self,
        *,
        lang: str = "por+eng",
        tesseract_cmd: str = "",
        tessdata_dir: str = "",
        engine: OcrEngine | None = None,
    ) -> None:
        self._lang = lang
        self._engine = engine or _default_engine(tesseract_cmd, tessdata_dir)

    async def capture(self, *, image: bytes, lang: str | None = None, **_params: object) -> Percept:
        """Reconhece o texto da ``image`` (no worker thread) e devolve um Percept.

        Args:
            image: Bytes da imagem (PNG/JPEG/…) a transcrever.
            lang: Sobrescreve o(s) idioma(s) do Tesseract para esta captura.

        Raises:
            SensorError: Se ``image`` estiver vazia ou a imagem for inválida.
            OcrUnavailableError: Se o Tesseract não estiver instalado/encontrado.
        """
        if not image:
            raise SensorError("OCR requer uma imagem (bytes vazios).")
        use_lang = lang or self._lang
        text = await asyncio.to_thread(self._engine, image, use_lang)
        text = text.strip()
        logger.info("ocr_captured", chars=len(text), lang=use_lang, bytes=len(image))
        return Percept(
            modality=Modality.OCR_TEXT,
            source_id=self.descriptor.id,
            data=text,
            mime="text/plain",
            metadata={"lang": use_lang, "chars": len(text)},
        )
