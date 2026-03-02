import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

const api = axios.create({
    baseURL: API_BASE,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request if available
api.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('saarthi_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// Handle 401 Unauthorized errors globally
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && [401, 403].includes(error.response.status)) {
            if (typeof window !== 'undefined') {
                localStorage.removeItem('saarthi_token');
                localStorage.removeItem('saarthi_user');
                // Redirect to login only if not already there
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    window.location.href = '/login';
                }
            }
        }
        return Promise.reject(error);
    }
);

// ─── Auth ──────────────────────────────────────────────
export const register = async (email: string, password: string, full_name: string, company_name: string) => {
    const { data } = await api.post('/auth/register', { email, password, full_name, company_name });
    return data;
};

export const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password });
    return data;
};

// ─── Dashboard ─────────────────────────────────────────
export const fetchDashboard = async () => {
    const { data } = await api.get('/dashboard');
    return data;
};

// ─── Campaigns ─────────────────────────────────────────
export const fetchCampaigns = async () => {
    const { data } = await api.get('/campaigns');
    return data;
};

export const createCampaign = async (name: string) => {
    const { data } = await api.post('/campaigns', { name });
    return data;
};

export const fetchCampaign = async (id: string) => {
    const { data } = await api.get(`/campaigns/${id}`);
    return data;
};

export const updateCampaign = async (id: string, payload: { name?: string; status?: string; sequence_config?: any[]; schedule_config?: any }) => {
    const { data } = await api.put(`/campaigns/${id}`, payload);
    return data;
};

// ─── Leads ─────────────────────────────────────────────
export const fetchLeads = async (params?: { campaign_id?: string; status?: string }) => {
    const { data } = await api.get('/leads', { params });
    return data;
};

export const generateLeads = async (payload: { industry: string; job_title: string; location: string; num_leads?: number }) => {
    const { data } = await api.post('/leads/generate', payload);
    return data;
};


export const createLead = async (payload: {
    campaign_id: string; name: string; company?: string; email: string;
    title?: string; location?: string; phone?: string; linkedin?: string;
    email_status?: string;
}) => {
    const { data } = await api.post('/leads', payload);
    return data;
};

export const fetchLead = async (id: string) => {
    const { data } = await api.get(`/leads/${id}`);
    return data;
};

export const deleteLead = async (id: string) => {
    const { data } = await api.delete(`/leads/${id}`);
    return data;
};

export const importLeadsCSV = async (file: File, campaign_id: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('campaign_id', campaign_id);
    const { data } = await api.post('/leads/import-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
};

// ─── Outreach ──────────────────────────────────────────
export const sendEmail = async (lead_id: string, subject: string, body: string) => {
    const { data } = await api.post('/outreach/send', { lead_id, subject, body });
    return data;
};

// ─── Inbox ─────────────────────────────────────────────
export const fetchConversations = async (filter?: string) => {
    const { data } = await api.get('/inbox/conversations', { params: filter ? { filter } : {} });
    return data;
};

export const fetchConversation = async (id: string) => {
    const { data } = await api.get(`/inbox/conversations/${id}`);
    return data;
};

export const sendReply = async (conversation_id: string, body: string) => {
    const { data } = await api.post('/inbox/reply', { conversation_id, body });
    return data;
};

// ─── Settings ──────────────────────────────────────────
export const fetchSettings = async () => {
    const { data } = await api.get('/settings');
    return data;
};

// ─── Billing ───────────────────────────────────────────
export const createCheckout = async (plan: string) => {
    const { data } = await api.post('/billing/create-checkout-session', null, { params: { plan } });
    return data;
};

export default api;
