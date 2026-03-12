import axios from 'axios';
import { getToken, removeToken } from './auth';

const API_BASE = '/api';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 30000, // 30s since AI calls can be slow
    headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
    const token = getToken();
    if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && [401, 403].includes(error.response.status)) {
            if (typeof window !== 'undefined') {
                removeToken();
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    window.location.href = '/login';
                }
            }
        }
        return Promise.reject(error);
    }
);

// ─── Auth ──────────────────────────────────────────────
export const register = async (email: string, password: string, organization_name: string) => {
    const { data } = await api.post('/auth/register', { email, password, organization_name });
    return data;
};

export const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password });
    return data;
};

export const fetchMe = async () => {
    const { data } = await api.get('/auth/me');
    return data;
};

// ─── Dashboard ─────────────────────────────────────────
export const fetchMetrics = async () => {
    const { data } = await api.get('/dashboard/metrics');
    return data;
};

export const fetchLeadGrowth = async (days: number = 30) => {
    const { data } = await api.get('/dashboard/lead-growth', { params: { days } });
    return data;
};

export const fetchEmailPerformance = async (days: number = 30) => {
    const { data } = await api.get('/dashboard/email-performance', { params: { days } });
    return data;
};

export const fetchRevenueMetrics = async () => {
    const { data } = await api.get('/dashboard/revenue');
    return data;
};

export const fetchRecentActivity = async (limit: number = 10) => {
    const { data } = await api.get('/dashboard/recent-activity', { params: { limit } });
    return data;
};

export const fetchAiUsage = async (days: number = 30) => {
    const { data } = await api.get('/dashboard/ai-usage', { params: { days } });
    return data;
};

// ─── Leads ─────────────────────────────────────────────
export const fetchLeads = async (params?: { industry?: string; status?: string; search?: string; skip?: number; limit?: number; campaign_id?: string }) => {
    const { data } = await api.get('/leads', { params });
    return data;
};

export const fetchLead = async (id: string) => {
    const { data } = await api.get(`/leads/${id}`);
    return data;
};

export const createLead = async (payload: any) => {
    const { data } = await api.post('/leads', payload);
    return data;
};

export const updateLead = async (id: string, payload: any) => {
    const { data } = await api.patch(`/leads/${id}`, payload);
    return data;
};

export const deleteLead = async (id: string) => {
    const { data } = await api.delete(`/leads/${id}`);
    return data;
};

export const bulkCreateLeads = async (leads: any[]) => {
    const { data } = await api.post('/leads/bulk-create', { leads });
    return data;
};

// ─── Campaigns ─────────────────────────────────────────
export const fetchCampaigns = async () => {
    const { data } = await api.get('/campaigns');
    return data;
};

export const fetchCampaign = async (id: string) => {
    const { data } = await api.get(`/campaigns/${id}`);
    return data;
};

export const createCampaign = async (payload: any) => {
    const { data } = await api.post('/campaigns', payload);
    return data;
};

export const updateCampaign = async (id: string, payload: any) => {
    const { data } = await api.patch(`/campaigns/${id}`, payload);
    return data;
};

export const startCampaign = async (id: string) => {
    const { data } = await api.post(`/campaigns/${id}/start`);
    return data;
};

export const pauseCampaign = async (id: string) => {
    const { data } = await api.post(`/campaigns/${id}/pause`);
    return data;
};

export const fetchCampaignEmails = async (id: string) => {
    const { data } = await api.get(`/campaigns/${id}/emails`);
    return data;
};

export const fetchCampaignStats = async (id: string) => {
    const { data } = await api.get(`/campaigns/${id}/stats`);
    return data;
};

// ─── Discovery (LeadGen) ───────────────────────────────
export const runDiscovery = async (payload: { industry: string; location: string; limit?: number }) => {
    const { data } = await api.post('/discovery/run', payload);
    return data;
};

export const fetchDiscoveryStatus = async (task_id: string) => {
    const { data } = await api.get(`/discovery/status/${task_id}`);
    return data;
};

// ─── Intelligence (AI) ─────────────────────────────────
export const scoreLead = async (lead_id: string) => {
    const { data } = await api.post('/intelligence/score', { lead_id });
    return data;
};

export const getLeadScore = async (lead_id: string) => {
    const { data } = await api.get(`/intelligence/score/${lead_id}`);
    return data;
};

export const enrichLead = async (lead_id: string) => {
    const { data } = await api.post('/intelligence/enrich', { lead_id });
    return data;
};

// ─── Inbox ─────────────────────────────────────────────
export const fetchInboxThreads = async (status?: string) => {
    const { data } = await api.get('/inbox', { params: { status } });
    return data;
};

export const fetchInboxMessages = async (thread_id: string) => {
    const { data } = await api.get(`/inbox/${thread_id}/messages`);
    return data;
};

export const processInbox = async () => {
    const { data } = await api.post('/inbox/process');
    return data;
};

export const replyToThread = async (thread_id: string) => {
    const { data } = await api.post(`/inbox/${thread_id}/reply`);
    return data;
};

export const classifyThread = async (thread_id: string) => {
    const { data } = await api.post(`/inbox/${thread_id}/classify`);
    return data;
};

// ─── Meetings ──────────────────────────────────────────
export const fetchMeetings = async () => {
    const { data } = await api.get('/meetings');
    return data;
};

export const createMeeting = async (payload: any) => {
    const { data } = await api.post('/meetings', payload);
    return data;
};

export const updateMeeting = async (id: string, payload: any) => {
    const { data } = await api.patch(`/meetings/${id}`, payload);
    return data;
};

export const deleteMeeting = async (id: string) => {
    const { data } = await api.delete(`/meetings/${id}`);
    return data;
};

export const sendMeetingConfirmation = async (id: string) => {
    const { data } = await api.post(`/meetings/${id}/send-confirmation`);
    return data;
};

// ─── Settings ──────────────────────────────────────────
export const fetchOrgSettings = async () => {
    const { data } = await api.get('/settings');
    return data;
};

export const updateOrgSettings = async (settings: any) => {
    const { data } = await api.patch('/settings', { settings });
    return data;
};

export const configureEmailIntegration = async (payload: { provider: string; configuration: any }) => {
    const { data } = await api.post('/settings/integrations/email', payload);
    return data;
};

export const configureCalendarIntegration = async (payload: { provider: string; configuration: any }) => {
    const { data } = await api.post('/settings/integrations/calendar', payload);
    return data;
};

export const fetchTasks = async (task_category: string) => {
    const { data } = await api.get('/tasks', { params: { category: task_category } });
    return data;
}

export const fetchSubscription = async () => {
    const { data } = await api.get('/billing/subscription');
    return data;
};

export default api;
