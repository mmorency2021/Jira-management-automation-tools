"""Google OAuth flow — provides authenticated gspread client and Google API services."""
from __future__ import annotations

from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CREDENTIALS = _PROJECT_ROOT / "credentials.json"
_TOKEN = _PROJECT_ROOT / "token.json"


def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if _TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDENTIALS.exists():
                raise FileNotFoundError(
                    f"Google credentials not found at {_CREDENTIALS}.\n"
                    "Download from Google Cloud Console > APIs & Services > Credentials.\n"
                    "See Phase 5 setup instructions in the plan."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)

        _TOKEN.write_text(creds.to_json())

    return creds


def get_gspread_client():
    import gspread
    creds = _get_credentials()
    return gspread.authorize(creds)


def get_slides_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    return build("slides", "v1", credentials=creds)


def get_drive_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds)
