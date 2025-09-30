# Real (ish) time Voice Chat

This project provides a local real (ish) time conversational interface with an LLM using speech-to-text (STT) and text-to-speech (TTS) pipelines that run fully on your machine. I am using LMStudio to run my local LLM. 

## Components

- `backend/`
  - FastAPI app with REST + WebSocket endpoints
  - STT worker using `WhisperModel` with GPU acceleration
  - TTS worker leveraging Kokoro ONNX (`af_heart` voice)
  - Streaming relay to LLM at `http://127.0.0.1:11434`
  - Conversation persistence layer (SQLite via SQLAlchemy)
  - Media storage rooted at `backend/data/media` for audio/image assets
  - Persistent conversation history stored locally (SQLite) that the UI can browse and resume.
- `frontend/`
  - PHP templates with vanilla JS modules
  - UI elements: conversation list, chat transcript, controls for mic selection, VAD sensitivity, voice toggle/volume slider, image attachment
  - Configuration panel to adjust LLM host/model and audio settings

## Getting started

1. **Prerequisites**
   - Python 3.11 (virtual environment recommended)
   - PHP 8+ (for the built-in development server)
   - LLM running locally with the `openai/gpt-oss-20b` model pulled (mistralai/magistral-small-2509 for image processing)
   - `kokoro.onnx` and `voices.bin` placed in the repository root (already gitignored)
   - Get kokoro components from https://github.com/thewh1teagle/kokoro-onnx

2. **Backend setup**
   ```
   python.exe -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Frontend setup**
   ```
   cd frontend/public
   php -S 127.0.0.1:8080 -t . router.php
   ```
   The PHP dev server will serve the static frontend while proxying API/WebSocket calls to the FastAPI backend.

## Notes

- Whisper model downloads will occur on first run.
- This is my first Github repository. Please be nice. I'm happy to fix problems, help, and learn!

