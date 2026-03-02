"""
Gmail Service — adapted from the existing saarthi/email_outreach/gmail_sender.py.

In SaaS mode, this reads OAuth credentials from the sending_accounts DB table
rather than from a local token.json file.

For the demo: falls back to mock mode when no credentials are configured.
"""

import os
import base64
import uuid
import structlog
from email.message import EmailMessage
from typing import Optional

log = structlog.get_logger(__name__)


class GmailService:
    """
    Sends emails via Gmail API using OAuth2 credentials.
    Returns dict with message_id and thread_id on success.
    Falls back to mock mode when credentials are not available.
    """

    def __init__(self, token_json: str = ""):
        self.service = None
        self.creds = None

        if token_json:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build

                self.creds = Credentials.from_authorized_user_info(
                    info=__import__("json").loads(token_json),
                    scopes=[
                        "https://www.googleapis.com/auth/gmail.send",
                        "https://www.googleapis.com/auth/gmail.readonly",
                    ],
                )
                if self.creds and self.creds.valid:
                    self.service = build("gmail", "v1", credentials=self.creds)
                    log.info("gmail.authenticated")
                elif self.creds and self.creds.expired and self.creds.refresh_token:
                    from google.auth.transport.requests import Request
                    self.creds.refresh(Request())
                    self.service = build("gmail", "v1", credentials=self.creds)
                    log.info("gmail.refreshed")
            except Exception as e:
                log.warning("gmail.auth_failed", error=str(e))

    async def send(
        self,
        to: str,
        subject: str,
        html_body: str,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> dict:
        if not self.service:
            # Mock mode
            mock_id = f"mock_{uuid.uuid4().hex[:12]}"
            log.info("gmail.mock_send", to=to, subject=subject)
            return {"message_id": mock_id, "thread_id": thread_id or mock_id}

        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject

        if reply_to_message_id:
            message["In-Reply-To"] = reply_to_message_id
            message["References"] = reply_to_message_id

        import re
        text = re.sub(r"<br\s*/?>", "\n", html_body, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        plain_text = re.sub(r"<[^>]+>", "", text).strip()
        message.set_content(plain_text)

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": encoded}
        if thread_id:
            body["threadId"] = thread_id

        import googleapiclient.errors
        try:
            sent = self.service.users().messages().send(userId="me", body=body).execute()
            result = {
                "message_id": sent["id"],
                "thread_id": sent.get("threadId", sent["id"]),
            }
            log.info("gmail.sent", to=to, message_id=result["message_id"])
            return result
        except googleapiclient.errors.HttpError as e:
            log.error("gmail.send_error", to=to, error=str(e))
            raise

    def list_inbox_messages(self, query: str = "is:inbox newer_than:1d") -> list[dict]:
        if not self.service:
            return []
        try:
            result = self.service.users().messages().list(
                userId="me", q=query, labelIds=["INBOX"]
            ).execute()
            return result.get("messages", [])
        except Exception as e:
            log.error("gmail.list_inbox_failed", error=str(e))
            return []

    def get_message(self, message_id: str) -> dict:
        if not self.service:
            return {}
        try:
            return self.service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
        except Exception as e:
            log.error("gmail.get_message_failed", error=str(e))
            return {}


def get_gmail_service(user_id, db=None) -> GmailService:
    """
    Factory: creates a GmailService for the given user.
    In production, this would look up the user's sending_account from DB.
    For now, returns mock-mode service.
    """
    # TODO: Load token_json from SendingAccount table
    return GmailService(token_json="")
