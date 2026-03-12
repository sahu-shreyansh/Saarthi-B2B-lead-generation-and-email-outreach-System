import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, ForeignKey, DateTime, 
    Text, Float, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.database import Base


def new_uuid():
    return uuid.uuid4()

def utc_now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    settings = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False) # admin, user, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    token_version = Column(Integer, default=1, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True) # Full name backup
    
    contact_email = Column(String(255), nullable=True)
    email_verified = Column(Boolean, default=False)
    
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True) # Legacy sync
    
    website = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    
    description = Column(Text, nullable=True)
    score = Column(Integer, default=0) # 0-100
    status = Column(String(50), default="pending", nullable=False) # pending, contacted, replied, interested, not_interested, bounced
    
    current_step_number = Column(Integer, default=0)
    next_action_at = Column(DateTime(timezone=True), nullable=True)
    
    source = Column(String(100), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Sequence(Base):
    __tablename__ = "sequences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SequenceStep(Base):
    __tablename__ = "sequence_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    sequence_id = Column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), default="email", nullable=False) # email, linkedin, call
    wait_days = Column(Integer, default=1)
    template_subject = Column(String(500), nullable=True)
    template_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sequence_id = Column(UUID(as_uuid=True), ForeignKey("sequences.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    target_score = Column(Integer, default=50)
    email_template = Column(Text, nullable=True) # Legacy, will use Sequence
    daily_limit = Column(Integer, default=100)
    status = Column(String(50), default="draft", nullable=False) 
    stats = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CampaignEmail(Base):
    __tablename__ = "campaign_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    sequence_step_id = Column(UUID(as_uuid=True), ForeignKey("sequence_steps.id", ondelete="SET NULL"), nullable=True)
    
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    message_id = Column(String(255), nullable=True, index=True) # SMTP Message-ID for reply matching
    
    status = Column(String(50), default="sent", nullable=False) # sent, pending, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class EmailReply(Base):
    __tablename__ = "email_replies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_email_id = Column(UUID(as_uuid=True), ForeignKey("campaign_emails.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(Text, nullable=True)
    intent = Column(String(50), default="unknown", nullable=False) # interested, not_interested, meeting_request, out_of_office
    received_at = Column(DateTime(timezone=True), default=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class InboxThread(Base):
    __tablename__ = "inbox_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String(500), nullable=True)
    status = Column(String(50), default="open", nullable=False) 
    latest_message_at = Column(DateTime(timezone=True), default=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class InboxMessage(Base):
    __tablename__ = "inbox_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("inbox_threads.id", ondelete="CASCADE"), nullable=False)
    direction = Column(String(50), nullable=False) # incoming, outgoing
    sender_email = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    intent = Column(String(50), default="unknown", nullable=False) 
    ai_response = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    received_at = Column(DateTime(timezone=True), default=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=30)
    meeting_link = Column(String(500), nullable=True)
    status = Column(String(50), default="scheduled", nullable=False) 
    calendar_event_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    task_name = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    progress = Column(Integer, default=0)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LeadGenerationJob(Base):
    __tablename__ = "lead_generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    total_requested = Column(Integer, default=50)
    total_found = Column(Integer, default=0)
    total_inserted = Column(Integer, default=0)
    status = Column(String(50), default="PENDING") 
    error_message = Column(Text, nullable=True)
    meta = Column(JSONB, default=dict)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False)
    factors = Column(JSONB, default=dict)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class SendingAccount(Base):
    __tablename__ = "sending_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String(100), nullable=False) # gmail, outlook, smtp
    email = Column(String(255), nullable=False)
    
    # For OAuth providers (Gmail/Outlook)
    refresh_token = Column(Text, nullable=True)
    
    # For SMTP provider
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_user = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True) # Should be encrypted in production
    smtp_encryption = Column(String(20), default="tls") # tls, ssl, none
    
    is_active = Column(Boolean, default=True)
    daily_limit = Column(Integer, default=50)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    plan = Column(String(50), default="FREE")
    monthly_credit_limit = Column(Integer, default=100)
    credits_used = Column(Integer, default=0)
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class UsageTracking(Base):
    __tablename__ = "usage_tracking"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    month = Column(String(7), nullable=False) # YYYY-MM
    emails_sent = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ProviderRateLimit(Base):
    __tablename__ = "provider_rate_limits"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    sending_account_id = Column(UUID(as_uuid=True), ForeignKey("sending_accounts.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False) # YYYY-MM-DD
    emails_sent_today = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class StripeEvent(Base):
    __tablename__ = "stripe_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    event_id = Column(String(255), unique=True, nullable=False)
    type = Column(String(255), nullable=False)
    payload = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AiUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    operation = Column(String(100), nullable=False)
    model = Column(String(50), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_estimate = Column(Numeric(10, 6), default=0.0)
    latency_ms = Column(Integer, default=0)
    request_id = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class WorkerLog(Base):
    __tablename__ = "worker_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    task_id = Column(String(255), nullable=False, index=True)
    task_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False) 
    worker = Column(String(255), nullable=True)
    runtime_seconds = Column(Numeric(10, 4), nullable=True)
    error_logs = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class LeadSource(Base):
    __tablename__ = "lead_sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), default="manual", nullable=False)  # manual, discovery, import
    configuration = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EmailEvent(Base):
    __tablename__ = "email_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_email_id = Column(UUID(as_uuid=True), ForeignKey("campaign_emails.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # sent, delivered, opened, clicked, bounced, unsubscribed
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
