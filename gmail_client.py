from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode

import streamlit as st
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
DEFAULT_REDIRECT_URI = "http://localhost:8505"
PROJECT_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = PROJECT_DIR / "credentials.json"
TOKEN_PATH = PROJECT_DIR / "token.json"


class GmailClientError(Exception):
    """Raised when Gmail authentication or draft creation cannot be completed safely."""


def get_redirect_uri() -> str:
    try:
        configured_uri = st.secrets.get("GOOGLE_REDIRECT_URI", "")
    except Exception:
        configured_uri = ""
    return os.getenv("GOOGLE_REDIRECT_URI", "").strip() or configured_uri.strip() or DEFAULT_REDIRECT_URI


def get_google_auth_url() -> tuple[str, str]:
    flow = _build_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url, state


def handle_google_oauth_callback(
    query_params: Mapping[str, Any],
    expected_state: str | None,
) -> None:
    oauth_error = _get_query_value(query_params, "error")
    oauth_code = _get_query_value(query_params, "code")
    returned_state = _get_query_value(query_params, "state")

    if oauth_error:
        raise GmailClientError(f"Google OAuth was cancelled or failed: {oauth_error}")

    if not oauth_code:
        raise GmailClientError("Google OAuth callback did not include an authorization code.")

    if not expected_state:
        raise GmailClientError("OAuth state is missing. Start Google sign-in again.")

    if returned_state != expected_state:
        raise GmailClientError("OAuth state mismatch. Start Google sign-in again.")

    flow = _build_flow(state=expected_state)

    try:
        flow.fetch_token(code=oauth_code)
    except Exception as exc:
        raise GmailClientError(_map_oauth_error(exc)) from exc

    credentials = flow.credentials
    if not credentials or not credentials.valid:
        raise GmailClientError("Google OAuth completed, but Gmail credentials were not issued correctly.")

    _save_token(credentials)


def get_gmail_auth_status() -> dict[str, str | bool]:
    credentials = _load_saved_credentials()
    if credentials and credentials.valid:
        return {
            "connected": True,
            "label": "Connected successfully",
            "detail": "Gmail OAuth token is available and ready for draft creation.",
        }
    return {
        "connected": False,
        "label": "Not connected",
        "detail": "Sign in with Google to enable Gmail draft creation with attachments.",
    }


def get_gmail_service():
    credentials = _load_saved_credentials()
    if not credentials or not credentials.valid:
        raise GmailClientError("Gmail is not authenticated yet. Please sign in with Google first.")

    try:
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        raise GmailClientError(f"Gmail API authentication failed: {exc}") from exc


def build_mime_message_with_attachments(
    recipient: str,
    subject: str,
    body: str,
    cv_pdf_bytes: bytes,
    cover_letter_pdf_bytes: bytes,
    cv_filename: str = "TBNZ_CV.pdf",
    cover_letter_filename: str = "TBNZ_Cover_Letter.pdf",
) -> str:
    if not isinstance(cv_pdf_bytes, (bytes, bytearray)):
        raise GmailClientError("CV PDF must be bytes.")
    if not isinstance(cover_letter_pdf_bytes, (bytes, bytearray)):
        raise GmailClientError("Cover letter PDF must be bytes.")

    message = MIMEMultipart("mixed")
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    for payload, filename in (
        (cv_pdf_bytes, cv_filename),
        (cover_letter_pdf_bytes, cover_letter_filename),
    ):
        attachment = MIMEApplication(payload, _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(attachment)

    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")


def create_gmail_draft_with_attachments(
    recipient: str,
    subject: str,
    body: str,
    cv_pdf_bytes: bytes,
    cover_letter_pdf_bytes: bytes,
    cv_filename: str = "TBNZ_CV.pdf",
    cover_letter_filename: str = "TBNZ_Cover_Letter.pdf",
) -> dict[str, Any]:
    if not recipient.strip():
        raise GmailClientError("Recruiter email is required to create a Gmail draft.")
    if not subject.strip():
        raise GmailClientError("Email subject is required to create a Gmail draft.")
    if not body.strip():
        raise GmailClientError("Email body is required to create a Gmail draft.")
    if not cv_pdf_bytes:
        raise GmailClientError("CV PDF attachment data is missing.")
    if not cover_letter_pdf_bytes:
        raise GmailClientError("Cover letter PDF attachment data is missing.")

    service = get_gmail_service()
    raw_message = build_mime_message_with_attachments(
        recipient=recipient,
        subject=subject,
        body=body,
        cv_pdf_bytes=cv_pdf_bytes,
        cover_letter_pdf_bytes=cover_letter_pdf_bytes,
        cv_filename=cv_filename,
        cover_letter_filename=cover_letter_filename,
    )

    try:
        return service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw_message}},
        ).execute()
    except HttpError as exc:
        raise GmailClientError(_map_gmail_http_error(exc)) from exc
    except Exception as exc:
        raise GmailClientError(f"Gmail draft creation failed: {exc}") from exc


def _load_web_client_config() -> dict[str, Any]:
    if not CREDENTIALS_PATH.exists():
        raise GmailClientError(
            "Missing credentials.json. Put a Google OAuth client file of type `web` in the project root."
        )

    try:
        config = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GmailClientError(f"Could not read credentials.json: {exc}") from exc

    if "web" not in config:
        raise GmailClientError(
            "credentials.json has the wrong type. Create a Google OAuth client of type `web`, not `installed`."
        )

    redirect_uris = config["web"].get("redirect_uris", [])
    redirect_uri = get_redirect_uri()
    if redirect_uris and redirect_uri not in redirect_uris:
        raise GmailClientError(
            "Redirect URI mismatch. Add "
            f"`{redirect_uri}` to the authorized redirect URIs for this Google OAuth web client."
        )

    return config


def _build_flow(state: str | None = None) -> Flow:
    flow = Flow.from_client_config(
        client_config=_load_web_client_config(),
        scopes=GMAIL_SCOPES,
        state=state,
    )
    flow.redirect_uri = get_redirect_uri()
    return flow


def _load_saved_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None

    try:
        credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)
    except Exception:
        return None

    if credentials.valid:
        return credentials

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            _save_token(credentials)
            return credentials
        except Exception:
            return None

    return None


def _save_token(credentials: Credentials) -> None:
    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")


def _get_query_value(query_params: Mapping[str, Any], key: str) -> str:
    value = query_params.get(key, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def _map_oauth_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()

    if "redirect_uri_mismatch" in lowered:
        return (
            "Redirect URI mismatch. The Google OAuth web client must allow "
            f"`{get_redirect_uri()}` exactly."
        )
    if "invalid_client" in lowered:
        return "Google OAuth client is invalid. Check credentials.json and confirm it belongs to the correct project."
    if "unauthorized_client" in lowered:
        return "Google OAuth client is not authorized for this flow. Use a `web` OAuth client."
    if "access_denied" in lowered:
        return "Google sign-in was denied. Sign in again and grant Gmail compose access."
    if "state" in lowered:
        return "OAuth state mismatch. Start Google sign-in again."

    return f"Google OAuth authentication failed: {message}"


def _map_gmail_http_error(exc: HttpError) -> str:
    status_code = getattr(getattr(exc, "resp", None), "status", None)
    error_text = str(exc)

    if status_code == 400:
        return f"Gmail rejected the draft request. Check recipient, subject, body, or attachments. {error_text}"
    if status_code in {401, 403}:
        return "Gmail API authentication failed. Sign in with Google again and confirm Gmail compose access."
    if status_code == 404:
        return "The Gmail API endpoint could not be reached. Confirm Gmail API is enabled for this Google project."
    if status_code == 429:
        return "Gmail API quota was exceeded. Wait and try again later."
    if status_code and status_code >= 500:
        return "Gmail API is temporarily unavailable. Try again later."

    return f"Gmail draft creation failed with a Gmail API error: {error_text}"
