export interface User {
    id: string;
    email: string;
    organization_id: string;
    role: string;
}

export interface OrganizationSettings {
    [key: string]: any;
}

export interface Organization {
    id: string;
    name: string;
    settings: OrganizationSettings;
}

export interface Lead {
    id: string;
    organization_id: string;
    company_name?: string;
    website?: string;
    industry?: string;
    location?: string;
    description?: string;
    contact_name?: string;
    contact_email?: string;
    score: number;
    status: string;
    source: string;
    metadata: Record<string, any>;
}

export interface Campaign {
    id: string;
    organization_id: string;
    name: string;
    target_score: number;
    email_template?: string;
    daily_limit: number;
    status: string;
    stats: {
        sent: number;
        opened: number;
        clicked: number;
        replied: number;
        bounced: number;
    };
    created_at: string;
    updated_at: string;
}

export interface CampaignEmail {
    id: string;
    campaign_id: string;
    lead_id: string;
    subject?: string;
    body?: string;
    status: string;
    sent_at?: string;
    created_at: string;
}

export interface InboxThread {
    id: string;
    organization_id: string;
    lead_id?: string;
    subject?: string;
    status: string;
    latest_message_at: string;
}

export interface InboxMessage {
    id: string;
    thread_id: string;
    direction: 'incoming' | 'outgoing';
    sender_email?: string;
    sender_name?: string;
    subject?: string;
    body?: string;
    intent: string;
    ai_response?: string;
    is_processed: boolean;
    received_at: string;
}

export interface Meeting {
    id: string;
    organization_id: string;
    lead_id: string;
    title: string;
    scheduled_time: string;
    duration_minutes: number;
    meeting_link?: string;
    status: string;
    calendar_event_id?: string;
    created_at: string;
    updated_at: string;
}

export interface DashboardMetrics {
    total_leads: number;
    qualified_leads: number;
    active_campaigns: number;
    emails_sent: number;
    replies_received: number;
    meetings_booked: number;
    conversion_rate: number;
}

export interface AITask {
    task_id: string;
    task_name: string;
    status: string; // 'QUEUED', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    progress: number;
    result?: string;
    error_message?: string;
}
