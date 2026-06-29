"""Edge TTS text-to-speech service."""

import asyncio
import io
import tempfile
from pathlib import Path

import edge_tts
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class EdgeTTSService:
    """Converts text to speech audio using Microsoft Edge TTS."""

    def __init__(self):
        settings = get_settings()
        self.voice = settings.edge_tts_voice
        self.rate = settings.edge_tts_rate
        self.pitch = settings.edge_tts_pitch

    async def synthesize(self, text: str) -> dict:
        start = __import__("time").perf_counter()
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        latency_ms = (__import__("time").perf_counter() - start) * 1000
        audio_data = audio_buffer.getvalue()

        return {
            "audio": audio_data,
            "format": "mp3",
            "duration_estimate_ms": len(audio_data) / 16,  # rough estimate
            "latency_ms": latency_ms,
            "text_length": len(text),
        }

    async def synthesize_to_file(self, text: str, output_path: str) -> dict:
        result = await self.synthesize(text)
        Path(output_path).write_bytes(result["audio"])
        result["file_path"] = output_path
        return result

    async def stream_synthesize(
        self, text: str, cancel_event: asyncio.Event | None = None
    ):
        """Stream audio chunks for low-latency playback with cancel support."""
        communicate = edge_tts.Communicate(
            text=text, voice=self.voice, rate=self.rate, pitch=self.pitch
        )
        async for chunk in communicate.stream():
            if cancel_event and cancel_event.is_set():
                logger.info("tts_stream_cancelled")
                break
            if chunk["type"] == "audio":
                yield chunk["data"]

    @staticmethod
    async def list_voices(language: str = "en") -> list[dict]:
        voices = await edge_tts.list_voices()
        return [
            {"name": v["Name"], "gender": v["Gender"], "locale": v["Locale"]}
            for v in voices
            if v["Locale"].startswith(language)
        ]
