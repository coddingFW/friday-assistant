"""Camada de STT (Speech-to-Text) — transcrição de voz local.

Espelha a camada de TTS: um contrato (:mod:`backend.stt.ports`) e adapters
concretos por trás de uma fábrica (Strategy Pattern). O provedor padrão usa o
Whisper local via faster-whisper (CTranslate2), 100% offline após baixar o modelo.
"""
