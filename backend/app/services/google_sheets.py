"""Google Sheets CRM integration."""

from datetime import datetime, timezone
from typing import Any

import gspread
import structlog
from google.oauth2.service_account import Credentials

from app.config import get_settings

logger = structlog.get_logger()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CRM_HEADERS = [
    "Timestamp",
    "Call ID",
    "Name",
    "Company",
    "Industry",
    "Employees",
    "Inbound Calls/mo",
    "Outbound Calls/mo",
    "Existing Solution",
    "Pain Points",
    "Budget",
    "Timeline",
    "Lead Score",
    "Lead Tier",
    "Email",
    "Phone",
    "Booking Scheduled",
    "Booking DateTime",
    "Call Summary",
    "Call Duration (s)",
    "Qualified",
]


class GoogleSheetsCRM:
    """Creates and updates lead records in Google Sheets."""

    def __init__(self):
        settings = get_settings()
        self.spreadsheet_id = settings.google_sheets_spreadsheet_id
        self.worksheet_name = settings.google_sheets_worksheet_name
        self._client: gspread.Client | None = None
        self._credentials_path = settings.google_sheets_credentials_path

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=SCOPES
            )
            self._client = gspread.authorize(creds)
        return self._client

    def _get_worksheet(self):
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        try:
            return spreadsheet.worksheet(self.worksheet_name)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(
                title=self.worksheet_name, rows=1000, cols=len(CRM_HEADERS)
            )
            ws.append_row(CRM_HEADERS)
            return ws

    async def create_lead_record(
        self,
        call_id: str,
        lead_data: dict[str, Any],
        scoring: dict[str, Any] | None,
        summary: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        try:
            ws = self._get_worksheet()
            row = [
                datetime.now(timezone.utc).isoformat(),
                call_id,
                lead_data.get("name", ""),
                lead_data.get("company_name", ""),
                lead_data.get("industry", ""),
                lead_data.get("employee_count", ""),
                lead_data.get("monthly_inbound_calls", ""),
                lead_data.get("monthly_outbound_calls", ""),
                lead_data.get("existing_solution", ""),
                "; ".join(lead_data.get("pain_points", [])),
                lead_data.get("budget_range", ""),
                lead_data.get("timeline", ""),
                scoring.get("total_score", "") if scoring else "",
                scoring.get("tier", "") if scoring else "",
                lead_data.get("email", ""),
                lead_data.get("phone", ""),
                lead_data.get("booking_scheduled", False),
                lead_data.get("booking_datetime", ""),
                summary,
                round(duration_seconds, 1),
                scoring.get("qualified_for_booking", False) if scoring else False,
            ]
            ws.append_row(row)
            logger.info("crm_record_created", call_id=call_id)
            return {"status": "created", "call_id": call_id}
        except Exception as e:
            logger.error("crm_record_failed", call_id=call_id, error=str(e))
            return {"status": "error", "error": str(e)}
