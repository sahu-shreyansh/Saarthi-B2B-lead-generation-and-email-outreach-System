import os
import aiosmtplib
import resend
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from email.message import EmailMessage
from loguru import logger
from typing import Dict, Any, Tuple

class EmailSenderService:
    @staticmethod
    async def send_email(
        provider: str,
        to_email: str,
        subject: str,
        body: str,
        from_email: str = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Routes the email to the correct provider: 'smtp', 'sendgrid', or 'resend'.
        Returns (success_bool, message_id_or_error, response_metadata)
        """
        provider = provider.lower()
        from_email = from_email or os.environ.get("SMTP_USER", "noreply@saarthi.io")

        try:
            if provider == "sendgrid":
                return await EmailSenderService._send_sendgrid(to_email, from_email, subject, body)
            elif provider == "resend":
                return await EmailSenderService._send_resend(to_email, from_email, subject, body)
            else:
                return await EmailSenderService._send_smtp(to_email, from_email, subject, body)
        except Exception as e:
            logger.error(f"Email failed to send via {provider}: {str(e)}")
            return False, str(e), {}

    @staticmethod
    async def _send_smtp(to_email: str, from_email: str, subject: str, body: str) -> Tuple[bool, str, Dict[str, Any]]:
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = int(os.environ.get("SMTP_PORT", 587))
        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_PASS", "")

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=host,
                port=port,
                start_tls=True,
                username=user,
                password=password,
            )
            # SMTP doesn't always give a clear external ID, return a local mock
            import uuid
            msg_id = f"<smtp-{uuid.uuid4()}@{host}>"
            return True, msg_id, {"provider": "smtp"}
        except Exception as e:
            raise e

    @staticmethod
    async def _send_sendgrid(to_email: str, from_email: str, subject: str, body: str) -> Tuple[bool, str, Dict[str, Any]]:
        api_key = os.environ.get("SENDGRID_API_KEY")
        if not api_key:
            raise ValueError("SENDGRID_API_KEY is not set")
            
        sg = SendGridAPIClient(api_key)
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )
        
        response = sg.send(message)
        if response.status_code in [200, 201, 202]:
            msg_id = response.headers.get("X-Message-Id", "unknown-sg-id")
            return True, msg_id, {"provider": "sendgrid", "status_code": response.status_code}
        else:
            raise Exception(f"SendGrid Error: {response.status_code} {response.body}")

    @staticmethod
    async def _send_resend(to_email: str, from_email: str, subject: str, body: str) -> Tuple[bool, str, Dict[str, Any]]:
        api_key = os.environ.get("RESEND_API_KEY")
        if not api_key:
            raise ValueError("RESEND_API_KEY is not set")
            
        resend.api_key = api_key
        
        response = resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "text": body
        })
        
        msg_id = response.get("id")
        if msg_id:
            return True, msg_id, {"provider": "resend", "id": msg_id}
        else:
            raise Exception(f"Resend Error: {response}")
