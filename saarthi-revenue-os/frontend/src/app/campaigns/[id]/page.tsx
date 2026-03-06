'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useCampaign, useUpdateCampaign, useStartCampaign, usePauseCampaign } from '@/hooks/useCampaigns';
import { useLeads } from '@/hooks/useLeads';
import { fetchCampaignStats, fetchCampaignEmails } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import {
    BarChart3, Users, Settings2,
    Send, Reply, AlertTriangle, ArrowLeft,
    Search, Save, Rocket, Mail, Sparkles,
    MoreHorizontal
} from 'lucide-react';

const SUB_TABS = [
    { key: 'analytics', label: 'Analytics', icon: BarChart3 },
    { key: 'leads', label: 'Leads', icon: Users },
    { key: 'template', label: 'Email Template', icon: Mail },
    { key: 'configurations', label: 'Configurations', icon: Settings2 },
];

export default function CampaignDetailPage() {
    const params = useParams();
    const router = useRouter();
    const campaignId = params.id as string;

    const [activeTab, setActiveTab] = useState('analytics');
    const [searchLeads, setSearchLeads] = useState('');

    const { data: campaign, isLoading: isCampaignLoading } = useCampaign(campaignId);

    // Form States
    const [emailTemplate, setEmailTemplate] = useState('');
    const [targetScore, setTargetScore] = useState<number>(0.7);
    const [dailyLimit, setDailyLimit] = useState<number>(50);

    const { data: stats } = useQuery({
        queryKey: ['campaignStats', campaignId],
        queryFn: () => fetchCampaignStats(campaignId),
        enabled: !!campaignId
    });

    const { data: leads = [], isLoading: isLeadsLoading } = useLeads({ campaign_id: campaignId });

    useEffect(() => {
        if (campaign) {
            setEmailTemplate(campaign.email_template || '');
            setTargetScore(campaign.target_score || 0.7);
            setDailyLimit(campaign.daily_limit || 50);
        }
    }, [campaign]);

    const launchMut = useStartCampaign();
    const pauseMut = usePauseCampaign();
    const saveConfigMut = useUpdateCampaign();

    const handleSaveConfig = () => {
        saveConfigMut.mutate({
            id: campaignId,
            ...campaign,
            email_template: emailTemplate,
            target_score: targetScore,
            daily_limit: dailyLimit,
        });
    };

    if (isCampaignLoading) return <div className="p-4 text-center text-muted">Loading campaign details...</div>;

    const filteredLeads = (leads as any[]).filter((l: any) =>
        l.contact_name?.toLowerCase().includes(searchLeads.toLowerCase()) ||
        l.contact_email?.toLowerCase().includes(searchLeads.toLowerCase())
    );

    return (
        <div className="flex h-full w-full">
            {/* Left Sidebar Sub-navigation */}
            <div style={{ width: 240, borderRight: '1px solid var(--border)', background: 'var(--bg-surface)' }} className="flex-col h-full shrink-0">
                <div className="p-3">
                    <button
                        onClick={() => router.push('/campaigns')}
                        className="btn btn-ghost w-full justify-start mb-4"
                    >
                        <ArrowLeft size={14} /> Back to Campaigns
                    </button>

                    <div className="px-2 mb-4">
                        <h3 className="text-section mb-1 truncate">{campaign?.name}</h3>
                        <span className={`badge ${campaign?.status === 'active' ? 'badge-success' : 'badge-gray'}`}>
                            {campaign?.status?.toUpperCase() || 'DRAFT'}
                        </span>
                    </div>

                    <nav className="flex-col gap-1">
                        {SUB_TABS.map(tab => {
                            const Icon = tab.icon;
                            const active = activeTab === tab.key;
                            return (
                                <button
                                    key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    className={`nav-item w-full justify-start ${active ? 'active bg-hover text-primary' : 'text-secondary'}`}
                                >
                                    <Icon size={16} />
                                    <span>{tab.label}</span>
                                </button>
                            );
                        })}
                    </nav>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">

                {/* Header Context */}
                <div className="flex items-end justify-between mb-4">
                    <div>
                        <h1 className="page-title">{SUB_TABS.find(t => t.key === activeTab)?.label}</h1>
                        <p className="text-meta">Configuring campaign details and outreach strategy</p>
                    </div>
                    {campaign?.status !== 'active' ? (
                        <button
                            className="btn btn-primary"
                            onClick={() => launchMut.mutate(campaignId)}
                            disabled={launchMut.isPending || !!saveConfigMut.isPending}
                        >
                            <Rocket size={16} /> {launchMut.isPending ? 'Launching...' : 'Activate Campaign'}
                        </button>
                    ) : (
                        <button
                            className="btn btn-warning"
                            onClick={() => pauseMut.mutate(campaignId)}
                            disabled={pauseMut.isPending}
                        >
                            Pause Campaign
                        </button>
                    )}
                </div>

                {/* ═══════ ANALYTICS TAB ═══════ */}
                {activeTab === 'analytics' && (
                    <div className="fade-in max-w-4xl">
                        {/* Stats Grid */}
                        <div className="grid-3 mb-4">
                            {[
                                { label: 'Emails Sent', value: (stats as any)?.sent ?? campaign?.stats?.sent ?? 0, icon: Send },
                                { label: 'Replies', value: (stats as any)?.replied ?? campaign?.stats?.replied ?? 0, icon: Reply },
                                { label: 'Bounced', value: (stats as any)?.bounced ?? campaign?.stats?.bounced ?? 0, icon: AlertTriangle },
                            ].map((s, i) => {
                                const Icon = s.icon;
                                return (
                                    <div key={i} className="card-flat p-4 flex items-center gap-3">
                                        <div className="flex items-center justify-center shrink-0" style={{ width: 40, height: 40, borderRadius: 'var(--radius-sm)', background: 'var(--bg-hover)' }}>
                                            <Icon size={18} color="var(--accent-primary)" />
                                        </div>
                                        <div>
                                            <div className="text-meta mb-1">{s.label}</div>
                                            <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>{s.value}</div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* ═══════ LEADS TAB ═══════ */}
                {activeTab === 'leads' && (
                    <div className="fade-in">
                        <div className="flex items-center gap-2 mb-3">
                            <div className="flex-1" />
                            <div className="relative" style={{ width: 280 }}>
                                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" style={{ pointerEvents: 'none' }} />
                                <input
                                    className="input w-full"
                                    style={{ paddingLeft: 34 }}
                                    placeholder="Search Leads By Name/Email"
                                    value={searchLeads}
                                    onChange={e => setSearchLeads(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Name</th><th>Email</th><th>Company</th><th>Score</th><th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {isLeadsLoading ? (
                                        <tr><td colSpan={5}><div className="empty-state">Loading leads...</div></td></tr>
                                    ) : filteredLeads.length === 0 ? (
                                        <tr><td colSpan={5}><div className="empty-state">No leads found in this campaign.</div></td></tr>
                                    ) : filteredLeads.map((l: any) => (
                                        <tr key={l.id}>
                                            <td style={{ fontWeight: 500 }}>{l.contact_name}</td>
                                            <td className="text-secondary">{l.contact_email}</td>
                                            <td className="text-secondary">{l.company_name || '—'}</td>
                                            <td className="text-secondary">{(l.score || 0).toFixed(2)}</td>
                                            <td>
                                                <span className={`badge ${l.status === 'new' ? 'badge-blue' : l.status === 'replied' ? 'badge-success' : 'badge-gray'}`}>
                                                    {l.status?.toUpperCase()}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* ═══════ EMAIL TEMPLATE TAB ═══════ */}
                {activeTab === 'template' && (
                    <div className="fade-in max-w-3xl">
                        <div className="card-flat p-5">
                            <h3 className="text-lg font-bold flex items-center gap-2 mb-4"><Sparkles size={18} color="var(--accent-primary)" /> AI Email Template</h3>
                            <p className="text-meta mb-4">Define the base prompt or standard template. Our AI agent will dynamically personalize this template for each outbound lead.</p>

                            <div className="form-group mb-4">
                                <textarea
                                    className="input leading-relaxed"
                                    rows={14}
                                    value={emailTemplate}
                                    onChange={e => setEmailTemplate(e.target.value)}
                                    placeholder="e.g. You are Alex, SDR for Saarthi. Draft an email to the lead explaining value prop..."
                                    style={{ resize: 'vertical' }}
                                />
                                <div className="text-xs text-muted mt-2">Use variables like {'{lead_name}'}, {'{company_name}'}, {'{sender_name}'} if using direct interpolation. If relying on LLM, write prompt instructions.</div>
                            </div>
                            <div className="flex justify-end pt-4 border-t border-border">
                                <button className="btn btn-primary" onClick={handleSaveConfig} disabled={saveConfigMut.isPending}>
                                    <Save size={14} /> {saveConfigMut.isPending ? 'Saving...' : 'Save Template'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ═══════ CONFIGURATIONS TAB ═══════ */}
                {activeTab === 'configurations' && (
                    <div className="fade-in max-w-xl">
                        <div className="card-flat p-4 mb-4">
                            <h3 className="text-section mb-1 flex items-center gap-2"><Settings2 size={18} /> Delivery Configuration</h3>
                            <p className="text-meta mb-4">Settings for targeting and limits.</p>

                            <div className="form-group mb-5">
                                <div className="flex justify-between items-center mb-1">
                                    <label className="font-semibold text-primary">Daily Volume Limit</label>
                                    <input className="input text-center w-24" type="number" value={dailyLimit} onChange={e => setDailyLimit(Number(e.target.value))} />
                                </div>
                                <p className="text-sm text-secondary">Max emails across this specific campaign per 24hrs.</p>
                            </div>

                            <div className="form-group mb-5 pt-4 border-t border-border">
                                <div className="flex justify-between items-center mb-1">
                                    <label className="font-semibold text-primary">Lead Qualification Score Gateway</label>
                                    <div className="flex items-center gap-2">
                                        <input className="input w-full" type="range" min="0" max="1" step="0.05" value={targetScore} onChange={e => setTargetScore(Number(e.target.value))} />
                                        <span className="font-mono text-sm">{targetScore.toFixed(2)}</span>
                                    </div>
                                </div>
                                <p className="text-sm text-secondary">Only leads scored above this threshold by the AI will be emailed.</p>
                            </div>

                            <div className="flex justify-end pt-3 border-t border-border">
                                <button className="btn btn-primary" onClick={handleSaveConfig} disabled={saveConfigMut.isPending}>
                                    <Save size={14} /> Save Config
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
