'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchMe, fetchOrgSettings, updateOrgSettings, configureEmailIntegration, configureCalendarIntegration } from '@/lib/api';
import { Building2, MessageSquare, Plug } from 'lucide-react';

const SECTIONS = [
    { key: 'org', label: 'Organization details', icon: Building2 },
    { key: 'integrations', label: 'Integrations', icon: Plug },
    { key: 'ai', label: 'AI Auto-Reply', icon: MessageSquare },
];

function SectionSkeleton() {
    return (
        <div style={{ padding: '28px 32px' }}>
            {[1, 2, 3].map(i => (
                <div key={i} className="form-group mb-4">
                    <div className="skeleton" style={{ height: 11, width: 90, marginBottom: 8 }} />
                    <div className="skeleton" style={{ height: 40, width: '100%', borderRadius: 8 }} />
                </div>
            ))}
        </div>
    );
}

export default function SettingsPage() {
    const qc = useQueryClient();
    const [activeSection, setActiveSection] = useState('org');

    const { data: user } = useQuery({ queryKey: ['me'], queryFn: fetchMe, retry: false });
    const { data: settings, isLoading } = useQuery({
        queryKey: ['settings'],
        queryFn: fetchOrgSettings,
        retry: false,
    });

    const mut = useMutation({
        mutationFn: (payload: any) => updateOrgSettings(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['settings'] });
            alert('Settings updated successfully');
        },
        onError: () => alert('Failed to update settings')
    });

    const emailMut = useMutation({
        mutationFn: (payload: { provider: string; configuration: any }) => configureEmailIntegration(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['settings'] });
            alert('Email integration configured successfully');
        },
        onError: () => alert('Failed to configure email integration')
    });

    const calendarMut = useMutation({
        mutationFn: (payload: { provider: string; configuration: any }) => configureCalendarIntegration(payload),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['settings'] });
            alert('Calendar integration configured successfully');
        },
        onError: () => alert('Failed to configure calendar integration')
    });

    const [localSettings, setLocalSettings] = useState<any>({});
    const [emailProvider, setEmailProvider] = useState('smtp');
    const [emailConfig, setEmailConfig] = useState<any>({});
    const [calProvider, setCalProvider] = useState('google');
    const [calConfig, setCalConfig] = useState<any>({});

    // initialize local state when settings loads
    if (settings && Object.keys(localSettings).length === 0) {
        setLocalSettings(settings);
        const integrations = settings.integrations || {};
        if (integrations.email) {
            setEmailProvider(integrations.email.provider || 'smtp');
            setEmailConfig(integrations.email.configuration || {});
        }
        if (integrations.calendar) {
            setCalProvider(integrations.calendar.provider || 'google');
            setCalConfig(integrations.calendar.configuration || {});
        }
    }

    const handleChange = (key: string, value: any) => {
        setLocalSettings((prev: any) => ({ ...prev, [key]: value }));
    };

    const handleSave = () => {
        mut.mutate(localSettings);
    };

    const renderSection = () => {
        if (isLoading) return <SectionSkeleton />;

        const org = settings?.organization;

        switch (activeSection) {
            case 'org':
                return (
                    <div style={{ padding: '28px 32px', maxWidth: 520 }}>
                        <h2 className="text-section" style={{ marginBottom: 20 }}>Organization Details</h2>
                        <div className="form-group mb-4">
                            <label className="input-label">Organization Name</label>
                            <input className="input" defaultValue={org?.name ?? ''} disabled />
                            <div className="text-xs text-muted mt-1">Managed via authentication provider</div>
                        </div>
                    </div>
                );
            case 'integrations':
                return (
                    <div style={{ padding: '28px 32px', maxWidth: 520 }}>
                        <h2 className="text-section" style={{ marginBottom: 20 }}>Email Integration</h2>
                        <div className="form-group mb-5">
                            <label className="input-label">Email Provider</label>
                            <select
                                className="input"
                                value={emailProvider}
                                onChange={e => setEmailProvider(e.target.value)}
                            >
                                <option value="smtp">Custom SMTP</option>
                                <option value="sendgrid">SendGrid</option>
                                <option value="resend">Resend</option>
                            </select>
                        </div>
                        {emailProvider === 'smtp' && (
                            <>
                                <div className="form-group mb-4">
                                    <label className="input-label">SMTP Host</label>
                                    <input className="input" placeholder="smtp.gmail.com" value={emailConfig.host || ''} onChange={e => setEmailConfig({ ...emailConfig, host: e.target.value })} />
                                </div>
                                <div className="form-group mb-4">
                                    <label className="input-label">SMTP Port</label>
                                    <input className="input" type="number" placeholder="587" value={emailConfig.port || ''} onChange={e => setEmailConfig({ ...emailConfig, port: e.target.value })} />
                                </div>
                                <div className="form-group mb-4">
                                    <label className="input-label">Username</label>
                                    <input className="input" placeholder="user@example.com" value={emailConfig.username || ''} onChange={e => setEmailConfig({ ...emailConfig, username: e.target.value })} />
                                </div>
                                <div className="form-group mb-4">
                                    <label className="input-label">Password</label>
                                    <input className="input" type="password" placeholder="••••••••" value={emailConfig.password || ''} onChange={e => setEmailConfig({ ...emailConfig, password: e.target.value })} />
                                </div>
                            </>
                        )}
                        {emailProvider === 'sendgrid' && (
                            <div className="form-group mb-4">
                                <label className="input-label">SendGrid API Key</label>
                                <input className="input" type="password" placeholder="SG.xxxx" value={emailConfig.api_key || ''} onChange={e => setEmailConfig({ ...emailConfig, api_key: e.target.value })} />
                            </div>
                        )}
                        {emailProvider === 'resend' && (
                            <div className="form-group mb-4">
                                <label className="input-label">Resend API Key</label>
                                <input className="input" type="password" placeholder="re_xxxx" value={emailConfig.api_key || ''} onChange={e => setEmailConfig({ ...emailConfig, api_key: e.target.value })} />
                            </div>
                        )}
                        <div style={{ marginTop: 16, marginBottom: 32 }}>
                            <button className="btn btn-primary" onClick={() => emailMut.mutate({ provider: emailProvider, configuration: emailConfig })} disabled={emailMut.isPending}>
                                {emailMut.isPending ? 'Saving...' : 'Save Email Config'}
                            </button>
                        </div>

                        <h2 className="text-section" style={{ marginBottom: 20 }}>Calendar Integration</h2>
                        <div className="form-group mb-5">
                            <label className="input-label">Calendar Provider</label>
                            <select
                                className="input"
                                value={calProvider}
                                onChange={e => setCalProvider(e.target.value)}
                            >
                                <option value="google">Google Calendar</option>
                                <option value="calendly">Calendly</option>
                            </select>
                        </div>
                        {calProvider === 'calendly' && (
                            <div className="form-group mb-4">
                                <label className="input-label">Calendly API Key</label>
                                <input className="input" type="password" placeholder="cal_xxxx" value={calConfig.api_key || ''} onChange={e => setCalConfig({ ...calConfig, api_key: e.target.value })} />
                            </div>
                        )}
                        {calProvider === 'google' && (
                            <>
                                <div className="form-group mb-4">
                                    <label className="input-label">Client ID</label>
                                    <input className="input" placeholder="xxxx.apps.googleusercontent.com" value={calConfig.client_id || ''} onChange={e => setCalConfig({ ...calConfig, client_id: e.target.value })} />
                                </div>
                                <div className="form-group mb-4">
                                    <label className="input-label">Client Secret</label>
                                    <input className="input" type="password" placeholder="GOCSPX-xxxx" value={calConfig.client_secret || ''} onChange={e => setCalConfig({ ...calConfig, client_secret: e.target.value })} />
                                </div>
                            </>
                        )}
                        <div style={{ marginTop: 16 }}>
                            <button className="btn btn-primary" onClick={() => calendarMut.mutate({ provider: calProvider, configuration: calConfig })} disabled={calendarMut.isPending}>
                                {calendarMut.isPending ? 'Saving...' : 'Save Calendar Config'}
                            </button>
                        </div>
                    </div>
                );
            case 'ai':
                return (
                    <div style={{ padding: '28px 32px', maxWidth: 520 }}>
                        <h2 className="text-section" style={{ marginBottom: 20 }}>AI Auto-Reply Configuration</h2>

                        <div className="flex items-start gap-3 mb-5 p-4 bg-hover border border-border rounded-md">
                            <input
                                type="checkbox"
                                id="autoReply"
                                className="mt-1"
                                checked={localSettings.auto_reply_enabled || false}
                                onChange={e => handleChange('auto_reply_enabled', e.target.checked)}
                            />
                            <div>
                                <label htmlFor="autoReply" className="font-semibold text-sm cursor-pointer block">Enable AI Auto-Replies</label>
                                <span className="text-xs text-secondary mt-1 block">Allow the AI to automatically draft and send replies to common inquiries and meeting requests.</span>
                            </div>
                        </div>

                        {localSettings.auto_reply_enabled && (
                            <div className="form-group mb-5 fade-in">
                                <label className="input-label">Auto-Reply Delay (Minutes)</label>
                                <input
                                    className="input"
                                    type="number"
                                    min="0"
                                    max="60"
                                    value={localSettings.auto_reply_delay_mins || 5}
                                    onChange={e => handleChange('auto_reply_delay_mins', parseInt(e.target.value))}
                                />
                                <div className="text-xs text-muted mt-1">Time to wait before sending an AI-generated reply.</div>
                            </div>
                        )}

                        <div style={{ marginTop: 24 }}>
                            <button className="btn btn-primary" onClick={handleSave} disabled={mut.isPending}>
                                {mut.isPending ? 'Saving...' : 'Save Settings'}
                            </button>
                        </div>
                    </div>
                );
            default: return null;
        }
    };

    return (
        <div>
            <div className="page-header">
                <div className="page-header-left">
                    <h1>Settings</h1>
                    <p>Manage your organization and account preferences</p>
                </div>
            </div>

            <div className="flex" style={{ gap: 0, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                {/* Settings Sidebar */}
                <div style={{ width: 220, borderRight: '1px solid var(--border)', padding: 12, flexShrink: 0 }}>
                    {SECTIONS.map(({ key, label, icon: Icon }) => (
                        <button
                            key={key}
                            className={`nav-item w-full${activeSection === key ? ' active' : ''}`}
                            style={{ border: 'none', width: '100%', background: activeSection === key ? 'var(--bg-hover)' : 'transparent', textAlign: 'left', marginBottom: 2 }}
                            onClick={() => setActiveSection(key)}
                        >
                            <Icon size={14} />
                            <span>{label}</span>
                        </button>
                    ))}
                </div>

                {/* Settings Content */}
                <div style={{ flex: 1 }}>
                    {renderSection()}
                </div>
            </div>
        </div>
    );
}
