import smtplib
import ssl
import uuid
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from app.database.models import Lead, SendingAccount

class EmailSender:
    @staticmethod
    def personalize_template(template: str, lead: Lead) -> str:
        """
        Replace {{field}} with lead data.
        Supported tags: first_name, last_name, company, title, website, etc.
        """
        if not template:
            return ""
            
        # Prepare data dictionary
        data = {
            "first_name": lead.first_name or (lead.contact_name.split(' ')[0] if lead.contact_name else "there"),
            "last_name": lead.last_name or "",
            "company": lead.company or lead.company_name or "your company",
            "title": lead.title or "Professional",
            "website": lead.website or "",
            "location": lead.location or ""
        }
        
        # Merge metadata for custom tags
        if lead.metadata_:
            for k, v in lead.metadata_.items():
                # Normalize key for matching (lowercase, no spaces)
                clean_k = k.lower().replace(" ", "_")
                if clean_k not in data:
                    data[clean_k] = str(v)

        result = template
        # Use regex to find all matches of {{tag}}
        matches = re.findall(r"\{\{([^}]+)\}\}", result)
        for tag in matches:
            clean_tag = tag.strip().lower().replace(" ", "_")
            if clean_tag in data:
                result = result.replace(f"{{{{{tag}}}}}", data[clean_tag])
            
        return result

    @staticmethod
    def send_email(
        account: SendingAccount,
        to_email: str,
        subject: str,
        body: str,
        thread_msg_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Send email via SMTP using the SendingAccount.
        Returns the Message-ID on success, None on failure.
        """
        if not account or not account.is_active:
            print(f"EMAIL_SENDER: Account {account.id if account else 'Unknown'} is inactive or missing.")
            return None

        # Prepare Message
        msg = MIMEMultipart()
        msg['From'] = f"{account.email}"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Generate a unique Message-ID for tracking
        domain = account.smtp_host or "saarthi.ai"
        msg_id = f"<{uuid.uuid4()}@{domain}>"
        msg['Message-ID'] = msg_id
        
        if thread_msg_id:
            # Threading headers
            msg['In-Reply-To'] = thread_msg_id
            msg['References'] = thread_msg_id

        msg.attach(MIMEText(body, 'plain'))

        try:
            # SMTP Connection
            if account.smtp_encryption == "ssl":
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, context=context, timeout=10)
            else:
                server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=10)
                if account.smtp_encryption == "tls":
                    server.starttls(context=ssl.create_default_context())
            
            # Login if credentials exist
            if account.smtp_user and account.smtp_password:
                server.login(account.smtp_user, account.smtp_password)
                
            server.send_message(msg)
            server.quit()
            
            print(f"EMAIL_SENDER: Successfully sent email to {to_email} via {account.email}")
            return msg_id
            
        except Exception as e:
            print(f"EMAIL_SENDER_ERROR: Failed to send to {to_email} via {account.email}: {str(e)}")
            return None
