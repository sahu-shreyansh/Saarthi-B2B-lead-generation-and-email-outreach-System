from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseProvider(ABC):
    """
    Abstract Base Class for Email Providers (Gmail, Outlook)
    """

    def __init__(self, token: str, refresh_token: str, client_id: str, client_secret: str, email_address: str):
        self.token = token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.email_address = email_address

    @abstractmethod
    def refresh_access_token(self) -> str:
        """
        Refresh the OAuth token. Returns the new access token.
        """
        pass

    @abstractmethod
    def send_email(self, to_email: str, subject: str, html_body: str, in_reply_to: str = None, references: str = None) -> Dict[str, str]:
        """
        Send an email.
        Must return a dict containing normalized:
        {
            "message_id": "...",
            "thread_id": "..."
        }
        """
        pass

    @abstractmethod
    def fetch_replies(self, since_timestamp: int) -> List[Dict[str, Any]]:
        """
        Fetch new messages in the inbox since the given timestamp.
        Must return normalized:
        [
            {
                "message_id": "...",
                "thread_id": "...",
                "from_email": "...",
                "body": "...",
                "date": datetime
            },
            ...
        ]
        """
        pass

    def normalize_thread_id(self, raw_thread_id: str) -> str:
        """
        Normalize the thread ID to be uniform internally across providers.
        """
        return raw_thread_id
