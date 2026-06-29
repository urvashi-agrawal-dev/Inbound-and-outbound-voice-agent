"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Karta SDR"
    app_env: str = "development"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change-me"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/karta_sdr"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_temperature: float = 0.3
    gemini_max_tokens: int = 512

    # Whisper
    whisper_model: str = "whisper-1"
    whisper_api_key: str = ""
    whisper_use_local: bool = False
    whisper_local_model: str = "base"

    # Edge TTS
    edge_tts_voice: str = "en-US-AriaNeural"
    edge_tts_rate: str = "+0%"
    edge_tts_pitch: str = "+0Hz"

    # Voice orchestration
    voice_provider: Literal["vapi", "livekit"] = "vapi"
    vapi_api_key: str = ""
    vapi_assistant_id: str = ""
    vapi_phone_number_id: str = ""
    vapi_webhook_secret: str = ""
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Google Sheets CRM
    google_sheets_credentials_path: str = "./credentials.json"
    google_sheets_spreadsheet_id: str = ""
    google_sheets_worksheet_name: str = "Leads"

    # Google Calendar
    google_calendar_credentials_path: str = "./credentials.json"
    google_calendar_id: str = "primary"
    google_calendar_timezone: str = "America/New_York"
    booking_duration_minutes: int = 30
    booking_buffer_minutes: int = 15

    # Lead scoring thresholds
    score_unqualified_max: int = 40
    score_warm_max: int = 80
    score_sql_max: int = 120

    # Conversation
    max_silence_seconds: int = 5
    barge_in_enabled: bool = True
    interruption_grace_ms: int = 300
    conversation_timeout_seconds: int = 1800
    faq_detour_max_turns: int = 3

    # Analytics
    cost_per_minute_usd: float = 0.08
    cost_per_llm_token_usd: float = 0.000001

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
