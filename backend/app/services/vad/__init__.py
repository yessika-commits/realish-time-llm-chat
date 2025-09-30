"""Voice activity detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import webrtcvad


@dataclass
class VADConfig:
    sample_rate: int = 16000
    frame_duration_ms: int = 30  # must be 10, 20, or 30 for webrtcvad
    silence_duration_ms: int = 1000


class VoiceActivityDetector:
    """Wraps webrtcvad to detect speech segments."""

    def __init__(self, aggressiveness: int = 2, config: VADConfig | None = None) -> None:
        if not 0 <= aggressiveness <= 3:
            raise ValueError("Aggressiveness must be between 0 and 3")
        self._vad = webrtcvad.Vad(aggressiveness)
        self._config = config or VADConfig()
        self._frame_bytes = int(self._config.sample_rate * (self._config.frame_duration_ms / 1000.0) * 2)

    @property
    def config(self) -> VADConfig:
        return self._config

    def trim_silence(self, pcm16: bytes) -> bytes:
        """Return PCM audio with leading/trailing silence removed."""
        frames = list(self._frame_generator(pcm16))
        if not frames:
            return pcm16

        speech_flags = [self._vad.is_speech(frame, self._config.sample_rate) for frame in frames]

        first_idx = None
        for idx, flag in enumerate(speech_flags):
            if flag:
                first_idx = idx
                break

        if first_idx is None:
            return b""  # Return empty if no speech is detected

        last_idx = None
        for offset, flag in enumerate(reversed(speech_flags)):
            if flag:
                last_idx = len(speech_flags) - offset - 1
                break

        assert last_idx is not None

        start_byte = first_idx * self._frame_bytes
        end_byte = min(len(pcm16), (last_idx + 1) * self._frame_bytes)
        return pcm16[start_byte:end_byte]

    def _frame_generator(self, pcm16: bytes) -> Iterable[bytes]:
        for i in range(0, len(pcm16), self._frame_bytes):
            yield pcm16[i : i + self._frame_bytes]