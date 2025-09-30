"""Application configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class LLMSettings(BaseModel):
    """Settings for LLM endpoint and model selection."""

    host: str = Field(default="http://127.0.0.1:11434", description="LLM base URL")
    #model: str = Field(default="openai/gpt-oss-20b", description="Model name to query")
    model: str = Field(default="mistralai/magistral-small-2509", description="Model name to query")
    system_prompt: str = Field(
        default=(
            "You are an AI voice assistant. Your responses will be converted to speech, "
            "so respond in natural sentences without markdown, lists, or special formatting. "
            "Never output JSON, code fences, tool calls, or commentary tags—only plain conversational text. "
            "Keep answers concise and to the point unless the user explicitly asks for detail. Short answers are better than long answers."
        ),
        description="System prompt prepended to every conversation",
    )


class AudioSettings(BaseModel):
    """Settings for audio processing parameters."""

    vad_silence_ms: int = Field(default=1500, description="Silence duration before auto-stop")
    enable_voice_output: bool = Field(default=True, description="Toggle for synthesizing speech")
    output_volume: float = Field(default=1.0, ge=0.0, le=1.5)
    kokoro_onnx_path: Path = Field(default=REPO_ROOT / "kokoro.onnx")
    kokoro_voices_path: Path = Field(default=REPO_ROOT / "voices.bin")
    kokoro_voice: str = Field(default="af_heart")
    input_dir: Path = Field(default=REPO_ROOT / "backend" / "data" / "media" / "audio" / "input")
    output_dir: Path = Field(default=REPO_ROOT / "backend" / "data" / "media" / "audio" / "responses")


class WhisperSettings(BaseModel):
    """Settings for the Whisper speech recognition model."""

    whisper_model_size: str = Field(default="distil-large-v3.5")
    device: str = Field(default="cuda")
    compute_type: str = Field(default="float16")
    download_root: Optional[Path] = None


class AppSettings(BaseSettings):
    """Top-level settings entry point."""

    model_config = SettingsConfigDict(
        env_prefix="REALTIME_CHAT_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    LLM: LLMSettings = LLMSettings()
    audio: AudioSettings = AudioSettings()
    whisper: WhisperSettings = WhisperSettings()
    conversation_db_path: Path = Field(default=REPO_ROOT / "backend" / "data" / "conversations.db")
    media_root: Path = Field(default=REPO_ROOT / "backend" / "data" / "media")


# A module-level cache for the settings instance provides a clearer singleton pattern.
_settings_instance: AppSettings | None = None


def get_settings() -> AppSettings:
    """Singleton accessor for settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings()
    return _settings_instance


def patch_settings(data: dict) -> AppSettings:
    """Apply a partial update to application settings at runtime."""
    global _settings_instance
    current = get_settings()
    new_settings = current.model_copy(update=data)
    _settings_instance = new_settings
    return new_settings