export type ReplyType = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'OOO' | 'EMPTY' | '';
export type ReplyStatus = 'NO_REPLY' | 'REPLIED' | string;
export type FollowupStatus = 'PENDING' | 'SENT' | 'STOPPED' | '';
export type DeliveryStatus = 'SENT' | 'FAILED' | 'BOUNCED' | '';
export type LeadStatus = 'NEW' | 'IN_SEQUENCE' | 'REPLIED' | 'CLOSED' | 'PENDING' | 'SENT' | string;

export interface Lead {
    lead_id: string;
    full_name: string | null;
    company: string | null;
    email: string | null;
    campaign: string;
    status: LeadStatus;
    category: string | null;
    last_contacted?: string;
    reply_status?: ReplyStatus;
    reply_type?: ReplyType;
    next_followup_due?: string;
    followup_status?: FollowupStatus;
    sequence_step?: number;
    delivery_status?: DeliveryStatus;
}

export interface OutreachEntry {
    outreach_id: string;
    sequence_step: number;
    gmail_thread_id: string;
    gmail_message_id: string;
    subject: string;
    email_body: string;
    sent_at: string;
    delivery_status: DeliveryStatus;
    reply_status: ReplyStatus;
    reply_type: ReplyType;
    reply_received_at: string;
    next_followup_due: string;
    followup_status: FollowupStatus;
}

export interface LeadDetail {
    lead_id: string;
    full_name: string | null;
    company: string | null;
    email: string | null;
    job_title: string | null;
    campaign: string;
    status: LeadStatus;
    category: string | null;
    ai_subject: string | null;
    ai_greeting_line1: string | null;
    ai_greeting_line2: string | null;
}

export interface Campaign {
    name: string;
    status: string;
    leads_enrolled: number;
    leads_by_status: Record<string, number>;
    reply_rate: number;
}

export interface DashboardData {
    metrics: {
        emails_sent_today: number;
        replies_today: number;
        positive_replies: number;
        followups_due_today: number;
    };
    active_campaigns: Record<string, number>;
    recent_replies: Array<{
        lead_id: string;
        reply_type: ReplyType;
        reply_received_at: string;
        subject: string;
    }>;
    followups_due: Array<{
        lead_id: string;
        sequence_step: number;
        next_followup_due: string;
        subject: string;
    }>;
}
