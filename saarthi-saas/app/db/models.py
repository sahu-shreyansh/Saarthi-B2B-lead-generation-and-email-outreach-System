import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean,
    ForeignKey, Date, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


# ── Users ─────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    campaigns = relationship("Campaign", back_populates="user", lazy="selectin")
    sending_accounts = relationship("SendingAccount", back_populates="user", lazy="selectin")
    subscription = relationship("Subscription", back_populates="user", uselist=False, lazy="selectin")


# ── Campaigns ─────────────────────────────────────
class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(20), default="active")  # active | paused
    sequence_config = Column(JSON, default=dict)   # stores array of steps
    schedule_config = Column(JSON, default=dict)   # stores days, times, limits
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="campaigns")
    leads = relationship("Lead", back_populates="campaign", lazy="selectin")


# ── Leads ─────────────────────────────────────────
class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company = Column(String(255), default="")
    email = Column(String(320), nullable=False)
    title = Column(String(255), default="")
    location = Column(String(255), default="")
    phone = Column(String(50), default="")
    linkedin = Column(String(500), default="")
    status = Column(String(40), default="NEW")  # NEW | IN_SEQUENCE | REPLIED | CLOSED
    email_status = Column(String(50), default="unknown")
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="leads")
    outreach_logs = relationship("OutreachLog", back_populates="lead", lazy="selectin")
    conversations = relationship("Conversation", back_populates="lead", lazy="selectin")


# ── Outreach Logs (append-only) ───────────────────
class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    sequence_step = Column(Integer, default=1)
    thread_id = Column(String(255), default="")
    message_id = Column(String(255), default="")
    subject = Column(String(500), default="")
    body = Column(Text, default="")
    sent_at = Column(DateTime, default=datetime.utcnow)
    reply_status = Column(String(20), default="NO_REPLY")    # NO_REPLY | REPLIED
    reply_type = Column(String(20), default="")               # POSITIVE | NEGATIVE | NEUTRAL | OOO
    followup_status = Column(String(20), default="PENDING")   # PENDING | STOPPED
    next_followup_due = Column(Date, nullable=True)

    lead = relationship("Lead", back_populates="outreach_logs")


# ── Conversations ─────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    thread_id = Column(String(255), unique=True, index=True)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", lazy="selectin",
                            order_by="Message.sent_at")


# ── Messages ──────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_type = Column(String(10), default="USER")  # USER | LEAD
    message_id = Column(String(255), default="")       # Gmail message ID
    subject = Column(String(500), default="")
    body = Column(Text, default="")
    sent_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


# ── Sending Accounts ──────────────────────────────
class SendingAccount(Base):
    __tablename__ = "sending_accounts"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(20), default="gmail")   # gmail | outlook (future)
    email = Column(String(320), nullable=False)
    access_token = Column(Text, default="")
    refresh_token = Column(Text, default="")
    token_json = Column(Text, default="")  # full serialized creds for Gmail API
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sending_accounts")


# ── Subscriptions ─────────────────────────────────
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), default="")
    stripe_subscription_id = Column(String(255), default="")
    plan_type = Column(String(40), default="free")      # free | starter | pro
    subscription_status = Column(String(40), default="active")  # active | canceled | past_due
    monthly_limit = Column(Integer, default=100)        # free tier: 100 emails
    current_period_end = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscription")


# ── Usage Tracking ────────────────────────────────
class UsageTracking(Base):
    __tablename__ = "usage_tracking"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    month = Column(String(7), nullable=False)  # YYYY-MM
    emails_sent = Column(Integer, default=0)
