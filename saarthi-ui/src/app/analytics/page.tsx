'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchDashboard, fetchCampaigns } from '@/lib/api';
import {
    Send, MailOpen, MousePointer, Reply,
    TrendingUp, BarChart3, Users, AlertTriangle, Target, XCircle
} from 'lucide-react';

export default function AnalyticsPage() {
    const { data: dashboard, isLoading: dashLoading } = useQuery({
        queryKey: ['dashboard'],
        queryFn: fetchDashboard,
    });
    const { data: campaigns = [], isLoading: campLoading, error: campError } = useQuery({
        queryKey: ['campaigns'],
        queryFn: fetchCampaigns,
    });

    const stats = [
        { label: 'Total Sent', value: dashboard?.total_sent ?? 0, icon: Send, color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' },
        { label: 'Emails Today', value: dashboard?.emails_sent_today ?? 0, icon: MailOpen, color: 'var(--accent-primary)', bg: 'rgba(20, 184, 166, 0.1)' },
        { label: 'Replies Today', value: dashboard?.replies_today ?? 0, icon: Reply, color: 'var(--success)', bg: 'rgba(16, 185, 129, 0.1)' },
        { label: 'Positive Replies', value: dashboard?.positive_replies ?? 0, icon: TrendingUp, color: 'var(--warning)', bg: 'rgba(245, 158, 11, 0.1)' },
        { label: 'Followups Due', value: dashboard?.followups_due ?? 0, icon: AlertTriangle, color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' },
        { label: 'Total Leads', value: dashboard?.total_leads ?? 0, icon: Users, color: '#a855f7', bg: 'rgba(168, 85, 247, 0.1)' },
    ];

    return (
        <div className="page-container fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Global Analytics</h1>
                    <p className="page-subtitle">High-level metrics across all connected accounts and active campaigns</p>
                </div>
            </div>

            {dashLoading && (
                <div className="card" style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <BarChart3 size={32} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
                    <p>Loading analytics data...</p>
                </div>
            )}

            {/* Stat cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
                {stats.map((s, i) => {
                    const Icon = s.icon;
                    return (
                        <div key={i} className="card fade-in" style={{ padding: 20, animationDelay: `${i * 0.04}s`, display: 'flex', flexDirection: 'column' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                                <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: s.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <Icon size={18} color={s.color} />
                                </div>
                                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>{s.label}</div>
                            </div>
                            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.03em' }}>{s.value}</div>
                        </div>
                    );
                })}
            </div>

            {/* Usage bar */}
            {dashboard && (
                <div className="card fade-in" style={{ padding: 24, marginBottom: 32, animationDelay: '0.3s' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Target size={16} color="var(--accent-primary)" />
                            <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Monthly Sending Capacity</span>
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                            <strong style={{ color: 'var(--text-primary)' }}>{dashboard.usage_sent}</strong> / {dashboard.usage_limit} emails
                        </div>
                    </div>
                    <div style={{ height: 10, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-full)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
                        <div style={{
                            height: '100%', borderRadius: 'var(--radius-full)',
                            width: `${Math.min((dashboard.usage_sent / Math.max(dashboard.usage_limit, 1)) * 100, 100)}%`,
                            background: 'linear-gradient(90deg, var(--accent-primary), #38bdf8)',
                            boxShadow: '0 0 10px var(--accent-glow)',
                            transition: 'width 1s ease-out',
                        }} />
                    </div>
                </div>
            )}

            {/* Campaign breakdown */}
            <div className="fade-in" style={{ animationDelay: '0.4s' }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <BarChart3 size={18} color="var(--accent-primary)" /> Campaign Performance
                </h2>

                {campError && (
                    <div style={{ padding: 20, background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                        <XCircle size={16} /> Error loading campaigns. Database might not be initialized.
                    </div>
                )}

                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Campaign Name</th>
                                <th>Status</th>
                                <th>Leads</th>
                                <th>Messages Sent</th>
                                <th>Reply Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {campLoading ? (
                                <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading records...</td></tr>
                            ) : campaigns.length === 0 ? (
                                <tr>
                                    <td colSpan={5} style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                                        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>No campaigns active</p>
                                        <p style={{ fontSize: 12, marginTop: 8 }}>Start a campaign to see performance metrics here.</p>
                                    </td>
                                </tr>
                            ) : campaigns.map((c: any) => (
                                <tr key={c.id}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</td>
                                    <td>
                                        <span className={`badge ${c.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                                            {c.status}
                                        </span>
                                    </td>
                                    <td>{c.leads_count ?? 0}</td>
                                    <td>{c.total_sent ?? 0}</td>
                                    <td>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <div style={{ flex: 1, height: 4, background: 'var(--bg-elevated)', borderRadius: 2 }}>
                                                <div style={{ height: '100%', width: `${c.reply_rate ?? 0}%`, background: 'var(--success)', borderRadius: 2 }} />
                                            </div>
                                            <span style={{ color: 'var(--success)', fontWeight: 700, fontSize: 13, width: 36 }}>{c.reply_rate ?? 0}%</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
