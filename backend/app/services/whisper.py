"""Whisper speech-to-text service."""

import io
from pathlib import Path

import httpx
import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()


class WhisperService:
    """Transcribes audio to text using OpenAI Whisper API or local model."""

    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.use_local = settings.whisper_use_local
        self._local_model = None
        if not self.use_local:
            self.client = AsyncOpenAI(api_key=settings.whisper_api_key)

    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str = "en",
    ) -> dict:
        if self.use_local:
            return await self._transcribe_local(audio_data)
        return await self._transcribe_api(audio_data, filename, language)

    async def _transcribe_api(
        self, audio_data: bytes, filename: str, language: str
    ) -> dict:
        start_event = __import__("time").perf_counter()
        audio_file = io.BytesIO(audio_data)
        audio_file.name = filename

        response = await self.client.audio.transcriptions.create(
            model=self.settings.whisper_model,
            file=audio_file,
            language=language,
            response_format="verbose_json",
        )

        latency_ms = (__import__("time").perf_counter() - start_event) * 1000
        text = response.text if hasattr(response, "text") else str(response)

        return {
            "text": text.strip(),
            "language": language,
            "latency_ms": latency_ms,
            "confidence": getattr(response, "duration", None),
        }

    async def _transcribe_local(self, audio_data: bytes) -> dict:
        import tempfile

        try:
            import whisper
        except ImportError:
            logger.error("whisper_not_installed", hint="pip install openai-whisper")
            raise

        if self._local_model is None:
            self._local_model = whisper.load_model(self.settings.whisper_local_model)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        start_event = __import__("time").perf_counter()
        result = self._local_model.transcribe(temp_path)
        latency_ms = (__import__("time").perf_counter() - start_event) * 1000
        Path(temp_path).unlink(missing_ok=True)

        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "latency_ms": latency_ms,
        }

    async def transcribe_url(self, audio_url: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            return await self.transcribe(response.content)
