"""Audio services for STT (Whisper) and TTS (Kokoro)."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
from pathlib import Path
from typing import Optional

import aiofiles
import numpy as np
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

from ..config import get_settings
from .vad import VoiceActivityDetector, VADConfig

logger = logging.getLogger(__name__)


class SpeechService:
    """Handles speech-to-text and text-to-speech pipelines."""

    def __init__(self) -> None:
        settings = get_settings()
        self._whisper_model: WhisperModel | None = None
        self._kokoro: Kokoro | None = None
        self._kokoro_voice = settings.audio.kokoro_voice
        self._onnx_path = settings.audio.kokoro_onnx_path
        self._voices_path = settings.audio.kokoro_voices_path
        self._enable_voice_output = settings.audio.enable_voice_output
        self._output_volume = settings.audio.output_volume
        self._input_dir = settings.audio.input_dir
        self._output_dir = settings.audio.output_dir
        self._vad = VoiceActivityDetector(
            aggressiveness=3,
            config=VADConfig(
                sample_rate=16000,
                frame_duration_ms=30,
                silence_duration_ms=settings.audio.vad_silence_ms,
            ),
        )

    async def initialize(self) -> None:
        if self._whisper_model is None:
            settings = get_settings()
            self._whisper_model = WhisperModel(
                settings.whisper.whisper_model_size,
                device=settings.whisper.device,
                compute_type=settings.whisper.compute_type,
                download_root=settings.whisper.download_root,
            )
        if self._kokoro is None and self._enable_voice_output:
            self._kokoro = Kokoro(
                model_path=str(self._onnx_path),
                voices_path=str(self._voices_path),
            )
        self._input_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def shutdown(self) -> None:
        if self._kokoro is not None:
            self._kokoro = None
        if self._whisper_model is not None:
            self._whisper_model = None

    async def transcribe_audio(self, audio_path: Path) -> str:
        if self._whisper_model is None:
            raise RuntimeError("SpeechService not initialized")

        segments, _ = await asyncio.to_thread(self._whisper_model.transcribe, str(audio_path))
        transcription = " ".join(segment.text.strip() for segment in segments)
        return transcription.strip()

    async def trim_silence(self, pcm16: bytes) -> bytes:
        return await asyncio.to_thread(self._vad.trim_silence, pcm16)

    async def synthesize_speech(self, text: str, output_path: Optional[Path] = None) -> Optional[Path]:
        if not self._enable_voice_output:
            logger.debug("Voice output disabled; skipping synthesis")
            return None
        if self._kokoro is None:
            raise RuntimeError("SpeechService not initialized for TTS")

        if output_path is None:
            filename = secrets.token_hex(8) + ".wav"
            output_path = self._output_dir / filename

        normalized_text = text.strip()
        if "*" in normalized_text:
            normalized_text = normalized_text.replace("*", "")
            normalized_text = re.sub(r" {2,}", " ", normalized_text)
        if not normalized_text:
            logger.debug("Skipping synthesis for empty text input")
            return None

        logger.debug("Synthesizing speech to %s", output_path)
        try:
            audio, sample_rate = await asyncio.to_thread(
                self._kokoro.create,
                normalized_text,
                self._kokoro_voice,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Kokoro synthesis failed: %s", exc)
            return None

        if self._output_volume != 1.0:
            audio = np.clip(audio * self._output_volume, -1.0, 1.0)

        await self._write_wav(output_path, audio, sample_rate=sample_rate)
        logger.debug("Synthesis complete: %s", output_path)
        return output_path

    async def _write_wav(self, output_path: Path, audio: np.ndarray, sample_rate: int = 22050) -> None:
        import wave

        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(output_path, "wb") as f:
            # wave module expects synchronous file object; write to buffer first
            data = await asyncio.to_thread(self._encode_wav, audio, sample_rate)
            await f.write(data)

    @staticmethod
    def _encode_wav(audio: np.ndarray, sample_rate: int) -> bytes:
        import io
        import wave

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            pcm16 = (audio * 32767).astype(np.int16)
            wav_file.writeframes(pcm16.tobytes())
        return buffer.getvalue()


_speech_service: SpeechService | None = None


async def get_speech_service() -> SpeechService:
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechService()
        await _speech_service.initialize()
    return _speech_service


async def shutdown_speech_service() -> None:
    global _speech_service
    if _speech_service is not None:
        await _speech_service.shutdown()
        _speech_service = None