'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchMe, fetchOrgSettings, updateOrgSettings, configureEmailIntegration, configureCalendarIntegration, fetchSubscription } from '@/lib/api';
import { Building2, MessageSquare, Plug, CreditCard, ExternalLink, Zap, Mail, ShieldCheck, BrainCircuit, Database } from 'lucide-react';
import { IntegrationsPanel } from '@/components/settings/IntegrationsPanel';
import { DatabasePanel } from '@/components/settings/DatabasePanel';

const SECTIONS = [
    { key: 'org', label: 'Organization details', icon: Building2 },
    { key: 'integrations', label: 'Integrations', icon: Plug },
    { key: 'database', label: 'Database', icon: Database },
    { key: 'ai', label: 'AI Auto-Reply', icon: MessageSquare },
    { key: 'billing', label: 'Billing & Usage', icon: CreditCard },
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

    const { data: subscription, isLoading: loadingSub } = useQuery({
        queryKey: ['subscription'],
        queryFn: fetchSubscription,
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

                        <div className="my-10 border-t border-border" />
                        
                        <div className="mb-8">
                            <h2 className="text-xl font-bold font-heading mb-1">AI & Intelligence Providers</h2>
                            <p className="text-sm text-secondary">Connect your own API keys to bypass platform limits and use custom models.</p>
                        </div>
                        
                        <IntegrationsPanel />
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
            case 'billing':
                if (loadingSub) return <SectionSkeleton />;
                return (
                    <div style={{ padding: '28px 32px', maxWidth: 640 }}>
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h2 className="text-xl font-bold font-heading">Billing & Subscription</h2>
                                <p className="text-sm text-secondary">Manage your plan and track resource usage</p>
                            </div>
                            <span className="px-3 py-1 bg-brand/10 text-brand border border-brand/20 rounded-full text-xs font-bold uppercase tracking-widest">
                                {subscription?.plan} Plan
                            </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
                            {/* Credits Usage */}
                            <div className="p-6 bg-[var(--bg-body)] border border-[var(--border)] rounded-2xl">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2 text-primary font-semibold">
                                        <Zap size={18} className="text-brand" />
                                        <span>AI Lead Credits</span>
                                    </div>
                                    <span className="text-xs text-secondary">Reset monthly</span>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-end">
                                        <span className="text-2xl font-bold font-heading text-primary">
                                            {subscription?.credits_used} <span className="text-sm text-secondary font-normal">/ {subscription?.monthly_credit_limit}</span>
                                        </span>
                                        <span className="text-xs text-secondary font-medium">
                                            {Math.round((subscription?.credits_used / subscription?.monthly_credit_limit) * 100)}% used
                                        </span>
                                    </div>
                                    <div className="w-full h-2 bg-[var(--bg-hover)] rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-brand transition-all duration-500"
                                            style={{ width: `${(subscription?.credits_used / subscription?.monthly_credit_limit) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Email Usage */}
                            <div className="p-6 bg-[var(--bg-body)] border border-[var(--border)] rounded-2xl">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2 text-primary font-semibold">
                                        <Mail size={18} className="text-success" />
                                        <span>Emails Sent</span>
                                    </div>
                                    <span className="text-xs text-secondary">Cycle: Monthly</span>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-end">
                                        <span className="text-2xl font-bold font-heading text-primary">
                                            {subscription?.emails_sent_this_month} <span className="text-sm text-secondary font-normal">/ {subscription?.monthly_credit_limit * 10}</span>
                                        </span>
                                        <span className="text-xs text-secondary font-medium">
                                            {Math.round((subscription?.emails_sent_this_month / (subscription?.monthly_credit_limit * 10)) * 100)}%
                                        </span>
                                    </div>
                                    <div className="w-full h-2 bg-[var(--bg-hover)] rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-success transition-all duration-500"
                                            style={{ width: `${(subscription?.emails_sent_this_month / (subscription?.monthly_credit_limit * 10)) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Subscription Card */}
                        <div className="p-6 bg-brand/[0.03] border border-brand/10 rounded-2xl flex items-center justify-between gap-6">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                    <ShieldCheck size={20} className="text-brand" />
                                    <h3 className="font-bold text-lg">Scale your outreach</h3>
                                </div>
                                <p className="text-sm text-secondary leading-relaxed">
                                    Get unlimited leads, higher sending limits, and advanced AI personalization by upgrading to a Pro plan.
                                </p>
                            </div>
                            <button className="btn btn-primary flex items-center gap-2 shrink-0 group">
                                Upgrade Plan
                                <ExternalLink size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                            </button>
                        </div>
                    </div>
                );
            case 'database':
                return (
                    <div style={{ padding: '28px 32px', maxWidth: 640 }}>
                        <div className="mb-8">
                            <h2 className="text-xl font-bold font-heading mb-1">Database Connectivity</h2>
                            <p className="text-sm text-secondary">Configure where your organization's data is stored. Managed by Saarthi or hosted on your own infrastructure.</p>
                        </div>
                        <DatabasePanel currentConfig={settings?.database_config} />
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
