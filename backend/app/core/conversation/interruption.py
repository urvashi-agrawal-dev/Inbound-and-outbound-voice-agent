"""Barge-in and interruption handling for real-time voice."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

import structlog

logger = structlog.get_logger()


class SpeechState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass
class InterruptionHandler:
    """
    Manages barge-in detection and graceful TTS cancellation.

    When the caller speaks while the agent is talking, we:
    1. Stop TTS playback immediately (within grace period)
    2. Buffer the new utterance
    3. Resume listening state
    4. Track interruption metrics
    """

    grace_ms: int = 300
    barge_in_enabled: bool = True
    speech_state: SpeechState = SpeechState.IDLE
    _tts_cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    _pending_utterance: str = ""
    interruption_count: int = 0

    def on_speech_start(self) -> None:
        """Called when VAD detects caller speech."""
        if (
            self.barge_in_enabled
            and self.speech_state == SpeechState.SPEAKING
        ):
            self._handle_barge_in()
        elif self.speech_state == SpeechState.IDLE:
            self.speech_state = SpeechState.LISTENING

    def _handle_barge_in(self) -> None:
        logger.info("barge_in_detected", grace_ms=self.grace_ms)
        self.speech_state = SpeechState.INTERRUPTED
        self.interruption_count += 1
        self._tts_cancel_event.set()

    def on_speech_end(self, transcript: str) -> str:
        """Finalize utterance after speech ends."""
        self._pending_utterance = transcript
        if self.speech_state in (SpeechState.LISTENING, SpeechState.INTERRUPTED):
            self.speech_state = SpeechState.PROCESSING
        return transcript

    def start_speaking(self) -> None:
        self._tts_cancel_event.clear()
        self.speech_state = SpeechState.SPEAKING

    def finish_speaking(self) -> None:
        self.speech_state = SpeechState.IDLE

    def was_interrupted(self) -> bool:
        return self.speech_state == SpeechState.INTERRUPTED

    async def speak_with_interrupt(
        self,
        tts_fn: Callable[[], Awaitable[None]],
        on_interrupt: Callable[[], Awaitable[None]] | None = None,
    ) -> bool:
        """
        Execute TTS with interrupt support.
        Returns True if completed without interruption.
        """
        self.start_speaking()
        tts_task = asyncio.create_task(tts_fn())
        cancel_task = asyncio.create_task(self._tts_cancel_event.wait())

        done, pending = await asyncio.wait(
            [tts_task, cancel_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.was_interrupted():
            if on_interrupt:
                await on_interrupt()
            return False

        self.finish_speaking()
        return True

    def reset(self) -> None:
        self.speech_state = SpeechState.IDLE
        self._pending_utterance = ""
        self._tts_cancel_event.clear()
