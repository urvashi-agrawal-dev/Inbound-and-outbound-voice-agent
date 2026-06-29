"""Google Calendar booking integration."""

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import get_settings

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    """Books demo meetings on Google Calendar for qualified leads."""

    def __init__(self):
        settings = get_settings()
        self.calendar_id = settings.google_calendar_id
        self.timezone = ZoneInfo(settings.google_calendar_timezone)
        self.duration_minutes = settings.booking_duration_minutes
        self.buffer_minutes = settings.booking_buffer_minutes
        self._service = None
        self._credentials_path = settings.google_calendar_credentials_path

    def _get_service(self):
        if self._service is None:
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=SCOPES
            )
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    async def get_available_slots(
        self, days_ahead: int = 7, max_slots: int = 10
    ) -> list[dict[str, str]]:
        service = self._get_service()
        now = datetime.now(self.timezone)
        time_min = now + timedelta(hours=24)
        time_max = now + timedelta(days=days_ahead)

        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        busy_times = []
        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            busy_times.append((datetime.fromisoformat(start), datetime.fromisoformat(end)))

        slots = []
        current = time_min.replace(minute=0, second=0, microsecond=0)
        if current.hour < 9:
            current = current.replace(hour=9)
        while current < time_max and len(slots) < max_slots:
            if 9 <= current.hour < 17 and current.weekday() < 5:
                slot_end = current + timedelta(minutes=self.duration_minutes)
                is_busy = any(
                    current < b_end and slot_end > b_start
                    for b_start, b_end in busy_times
                )
                if not is_busy:
                    slots.append({
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                        "display": current.strftime("%A, %B %d at %I:%M %p"),
                    })
            current += timedelta(minutes=self.duration_minutes + self.buffer_minutes)

        return slots

    async def book_meeting(
        self,
        attendee_email: str,
        attendee_name: str,
        company_name: str,
        preferred_time: str | None = None,
        call_id: str | None = None,
    ) -> dict[str, Any]:
        service = self._get_service()

        if preferred_time:
            try:
                start = datetime.fromisoformat(preferred_time)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=self.timezone)
            except ValueError:
                slots = await self.get_available_slots(max_slots=1)
                if not slots:
                    return {"status": "error", "error": "No available slots"}
                start = datetime.fromisoformat(slots[0]["start"])
        else:
            slots = await self.get_available_slots(max_slots=1)
            if not slots:
                return {"status": "error", "error": "No available slots"}
            start = datetime.fromisoformat(slots[0]["start"])

        end = start + timedelta(minutes=self.duration_minutes)
        event = {
            "summary": f"Karta SDR Demo - {company_name}",
            "description": (
                f"Demo call with {attendee_name} from {company_name}.\n"
                f"Qualified via AI SDR call (ID: {call_id or 'N/A'})."
            ),
            "start": {"dateTime": start.isoformat(), "timeZone": str(self.timezone)},
            "end": {"dateTime": end.isoformat(), "timeZone": str(self.timezone)},
            "attendees": [{"email": attendee_email}],
            "reminders": {"useDefault": True},
        }

        try:
            created = service.events().insert(
                calendarId=self.calendar_id, body=event, sendUpdates="all"
            ).execute()
            logger.info("meeting_booked", event_id=created["id"], call_id=call_id)
            return {
                "status": "booked",
                "event_id": created["id"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "html_link": created.get("htmlLink"),
            }
        except Exception as e:
            logger.error("booking_failed", error=str(e), call_id=call_id)
            return {"status": "error", "error": str(e)}
