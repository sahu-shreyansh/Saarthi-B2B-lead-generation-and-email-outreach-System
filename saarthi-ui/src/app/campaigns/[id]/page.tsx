'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCampaign, fetchLeads, sendEmail, importLeadsCSV, updateCampaign } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import {
    BarChart3, Users, Link2, CalendarDays, Settings2,
    Send, MailOpen, Reply, AlertTriangle, MousePointer,
    ArrowLeft, Plus, Upload, Search, Filter, Trash2, X,
    Play, Save, Rocket, Clock, Mail, PenTool, Sparkles, CheckCircle2
} from 'lucide-react';

const SUB_TABS = [
    { key: 'analytics', label: 'Analytics', icon: BarChart3 },
    { key: 'leads', label: 'Leads', icon: Users },
    { key: 'sequences', label: 'Sequences', icon: Link2 },
    { key: 'schedule', label: 'Schedule', icon: CalendarDays },
    { key: 'configurations', label: 'Configurations', icon: Settings2 },
];

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function CampaignDetailPage() {
    const params = useParams();
    const router = useRouter();
    const qc = useQueryClient();
    const campaignId = params.id as string;

    const [activeTab, setActiveTab] = useState('analytics');
    const [searchLeads, setSearchLeads] = useState('');
    const [showImport, setShowImport] = useState(false);
    const [importFile, setImportFile] = useState<File | null>(null);
    const [showAddStep, setShowAddStep] = useState(false);
    const [showEmailEditor, setShowEmailEditor] = useState(false);
    const [emailSubject, setEmailSubject] = useState('');
    const [emailBody, setEmailBody] = useState('');
    const [selectedDays, setSelectedDays] = useState([1, 2, 3, 4, 5]);
    const [scheduleStart, setScheduleStart] = useState('9:00 AM');
    const [scheduleEnd, setScheduleEnd] = useState('6:00 PM');
    const [dailyLimit, setDailyLimit] = useState(20);
    const [timeGapMin, setTimeGapMin] = useState(3);
    const [timeGapRandom, setTimeGapRandom] = useState(2);
    const [configTab, setConfigTab] = useState('Limit');
    const [sequenceSteps, setSequenceSteps] = useState<any[]>([]);
    const [analyticsTab, setAnalyticsTab] = useState('stepAnalytics');

    const { data: campaign, isLoading } = useQuery({
        queryKey: ['campaign', campaignId],
        queryFn: () => fetchCampaign(campaignId),
    });

    // Sync from server state once loaded
    useEffect(() => {
        if (campaign) {
            if (campaign.sequence_config && Array.isArray(campaign.sequence_config)) {
                setSequenceSteps(campaign.sequence_config);
            }
            if (campaign.schedule_config && campaign.schedule_config.days) {
                setSelectedDays(campaign.schedule_config.days);
                setScheduleStart(campaign.schedule_config.start);
                setScheduleEnd(campaign.schedule_config.end);
                setDailyLimit(campaign.schedule_config.daily_limit);
                setTimeGapMin(campaign.schedule_config.time_gap_min);
                setTimeGapRandom(campaign.schedule_config.time_gap_random);
            }
        }
    }, [campaign]);

    const { data: leads = [] } = useQuery({
        queryKey: ['leads', campaignId],
        queryFn: () => fetchLeads({ campaign_id: campaignId }),
    });

    const importMut = useMutation({
        mutationFn: (file: File) => importLeadsCSV(file, campaignId),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['leads', campaignId] });
            setShowImport(false);
            setImportFile(null);
        },
    });

    const launchMut = useMutation({
        mutationFn: () => updateCampaign(campaignId, { status: 'active' }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['campaign', campaignId] }),
        onError: (err: any) => alert(err?.response?.data?.detail || 'Failed to launch'),
    });

    const saveConfigMut = useMutation({
        mutationFn: () => updateCampaign(campaignId, {
            sequence_config: sequenceSteps,
            schedule_config: {
                days: selectedDays,
                start: scheduleStart,
                end: scheduleEnd,
                daily_limit: dailyLimit,
                time_gap_min: timeGapMin,
                time_gap_random: timeGapRandom
            }
        }),
        onSuccess: () => alert('Configuration saved!'),
        onError: (err: any) => alert(err?.response?.data?.detail || 'Failed to save config'),
    });

    if (isLoading) return <div className="page-container" style={{ textAlign: 'center', paddingTop: 100, color: 'var(--text-muted)' }}>Loading campaign details...</div>;

    const filteredLeads = leads.filter((l: any) =>
        l.name?.toLowerCase().includes(searchLeads.toLowerCase()) ||
        l.email?.toLowerCase().includes(searchLeads.toLowerCase())
    );

    const totalLeads = leads.length;
    const completedLeads = leads.filter((l: any) => l.status === 'REPLIED' || l.status === 'CLOSED').length;

    const toggleDay = (d: number) => {
        setSelectedDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
    };

    const addSequenceStep = (type: string) => {
        setSequenceSteps(prev => [...prev, {
            id: Date.now(),
            type,
            subject: emailSubject || 'New email',
            body: emailBody || '',
            delay: prev.length === 0 ? 0 : 1,
        }]);
        setShowAddStep(false);
        setShowEmailEditor(false);
        setEmailSubject('');
        setEmailBody('');
    };

    return (
        <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-base)' }}>
            {/* Left Sidebar Sub-navigation */}
            <div style={{
                width: 240, minWidth: 240, background: 'var(--bg-surface)',
                borderRight: '1px solid var(--border-subtle)',
                display: 'flex', flexDirection: 'column',
                padding: '24px 0',
                zIndex: 5,
            }}>
                {/* Back */}
                <button
                    onClick={() => router.push('/campaigns')}
                    className="btn btn-ghost"
                    style={{ margin: '0 16px 20px', justifyContent: 'flex-start', padding: '8px 12px' }}
                >
                    <ArrowLeft size={14} /> All Campaigns
                </button>

                {/* Campaign Name */}
                <div style={{ padding: '0 20px', marginBottom: 32 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, lineHeight: 1.3 }}>{campaign?.name}</h3>
                    <div className={`badge ${campaign?.status === 'active' ? 'badge-green' : 'badge-gray'}`} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                        {campaign?.status === 'active' ? <><div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--success)' }} /> Active</> : 'Paused'}
                    </div>
                </div>

                {/* Sub-tabs */}
                <nav style={{ padding: '0 12px' }}>
                    {SUB_TABS.map(tab => {
                        const Icon = tab.icon;
                        const active = activeTab === tab.key;
                        return (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '10px 16px', width: '100%',
                                    background: active ? 'var(--bg-hover)' : 'transparent',
                                    border: 'none', borderRadius: 'var(--radius-sm)',
                                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    fontSize: 13, fontWeight: active ? 600 : 500,
                                    cursor: 'pointer', textAlign: 'left',
                                    transition: 'all 0.2s ease',
                                    marginBottom: 4,
                                    boxShadow: active ? 'inset 3px 0 0 var(--accent-primary)' : 'none'
                                }}
                            >
                                <Icon size={16} color={active ? 'var(--accent-primary)' : 'currentColor'} />
                                {tab.label}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Main Content */}
            <div style={{ flex: 1, overflow: 'auto', padding: '32px 48px' }}>

                {/* Header Context */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 32 }}>
                    <div>
                        <h1 className="page-title">{SUB_TABS.find(t => t.key === activeTab)?.label}</h1>
                        <p className="page-subtitle">Configuring campaign details and outreach strategy</p>
                    </div>
                    {campaign?.status !== 'active' && activeTab === 'configurations' && (
                        <button
                            className="btn btn-primary"
                            style={{ padding: '10px 20px', fontSize: 13, background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', border: 'none' }}
                            onClick={() => launchMut.mutate()}
                            disabled={launchMut.isPending}
                        >
                            <Rocket size={16} /> {launchMut.isPending ? 'Launching...' : 'Launch Campaign'}
                        </button>
                    )}
                </div>

                {/* ═══════ ANALYTICS TAB ═══════ */}
                {activeTab === 'analytics' && (
                    <div className="fade-in">
                        {/* Date range controls */}
                        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
                            <select style={{ width: 150 }}>
                                <option>Past 4 Weeks</option>
                                <option>Past 7 Days</option>
                            </select>
                            <button className="btn btn-secondary"><Filter size={14} /> Custom Range</button>
                        </div>

                        {/* Chart placeholder */}
                        <div className="card" style={{ padding: 24, marginBottom: 24, height: 240, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                            <BarChart3 size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
                            <span>Analytics chart will appear here when campaign creates data</span>
                        </div>

                        {/* Stats */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 32 }}>
                            {[
                                { label: 'Emails Sent', value: campaign?.total_sent ?? 0, icon: Send, color: '#38bdf8' },
                                { label: 'Bounced', value: 0, icon: AlertTriangle, color: 'var(--danger)' },
                                { label: 'Opened', value: 0, icon: MailOpen, color: 'var(--warning)' },
                                { label: 'Replied', value: campaign?.replied ?? 0, icon: Reply, color: 'var(--success)' },
                            ].map((s, i) => {
                                const Icon = s.icon;
                                return (
                                    <div key={i} className="card" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: 16 }}>
                                        <div style={{ width: 44, height: 44, borderRadius: 'var(--radius-sm)', background: `rgba(${s.color === '#38bdf8' ? '56,189,248' : s.color === 'var(--danger)' ? '239,68,68' : s.color === 'var(--warning)' ? '245,158,11' : '16,185,129'}, 0.1)`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            <Icon size={20} color={s.color} />
                                        </div>
                                        <div>
                                            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500, marginBottom: 2 }}>{s.label}</div>
                                            <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.03em' }}>{s.value}</div>
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
                        {/* Lead Counts */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
                            {[
                                { label: 'Total Leads', value: totalLeads, color: 'var(--accent-primary)' },
                                { label: 'Completed', value: completedLeads, color: 'var(--success)' },
                                { label: 'Unsubscribed', value: 0, color: 'var(--warning)' },
                                { label: 'Bounced', value: 0, color: 'var(--danger)' },
                            ].map((s, i) => (
                                <div key={i} className="card" style={{ padding: '16px 20px' }}>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500, marginBottom: 4 }}>{s.label}</div>
                                    <div style={{ fontSize: 24, fontWeight: 700, color: s.color, letterSpacing: '-0.02em' }}>{s.value}</div>
                                </div>
                            ))}
                        </div>

                        {/* Controls */}
                        <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center' }}>
                            <button className="btn btn-primary" onClick={() => setShowImport(true)}>
                                <Upload size={14} /> Import CSV
                            </button>
                            <div style={{ flex: 1 }} />
                            <div style={{ position: 'relative', width: 260 }}>
                                <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                                <input
                                    value={searchLeads}
                                    onChange={e => setSearchLeads(e.target.value)}
                                    placeholder="Search Leads By Name"
                                    style={{ paddingLeft: 36, width: '100%', background: 'var(--bg-elevated)' }}
                                />
                            </div>
                        </div>

                        {/* Leads Table */}
                        <div className="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th style={{ width: 30 }}><input type="checkbox" /></th>
                                        <th>Name</th><th>Email</th><th>Company</th><th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredLeads.length === 0 ? (
                                        <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No leads found in this campaign</td></tr>
                                    ) : filteredLeads.map((l: any) => (
                                        <tr key={l.id}>
                                            <td><input type="checkbox" /></td>
                                            <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{l.name}</td>
                                            <td style={{ color: 'var(--text-secondary)' }}>{l.email}</td>
                                            <td>{l.company || '—'}</td>
                                            <td>
                                                <span className={`badge ${l.status === 'NEW' ? 'badge-blue' : l.status === 'REPLIED' ? 'badge-green' : 'badge-gray'}`}>
                                                    {l.status}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* ═══════ SEQUENCES TAB ═══════ */}
                {activeTab === 'sequences' && (
                    <div className="fade-in" style={{ maxWidth: 800 }}>
                        {/* Existing steps */}
                        {sequenceSteps.length > 0 && (
                            <div style={{ marginBottom: 32, position: 'relative' }}>
                                {/* Timeline line */}
                                <div style={{ position: 'absolute', left: 20, top: 40, bottom: 20, width: 2, background: 'var(--border-subtle)', zIndex: 0 }} />

                                {sequenceSteps.map((step, idx) => (
                                    <div key={step.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 20, marginBottom: 24, position: 'relative', zIndex: 1 }}>
                                        {/* Step Node */}
                                        <div style={{
                                            width: 40, height: 40, borderRadius: '50%',
                                            background: 'var(--bg-surface)', border: '2px solid var(--accent-primary)', color: 'var(--accent-primary)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: 14, fontWeight: 700, flexShrink: 0,
                                            boxShadow: '0 0 15px rgba(20, 184, 166, 0.2)'
                                        }}>
                                            {idx + 1}
                                        </div>

                                        {/* Step Card */}
                                        <div className="card" style={{ flex: 1, padding: 20 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                                    <Mail size={16} color="var(--accent-primary)" />
                                                    <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{step.subject}</span>
                                                </div>
                                                {idx > 0 && (
                                                    <span className="badge badge-gray" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                                        <Clock size={10} /> Wait {step.delay} day
                                                    </span>
                                                )}
                                            </div>
                                            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, background: 'var(--bg-elevated)', padding: 16, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                                                {step.body ? (
                                                    <div style={{ whiteSpace: 'pre-wrap' }}>{step.body.substring(0, 150)}{step.body.length > 150 ? '...' : ''}</div>
                                                ) : 'No content added yet'}
                                            </div>
                                            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                                                <button className="btn btn-secondary" style={{ fontSize: 12, padding: '6px 14px' }} onClick={() => {
                                                    setEmailSubject(step.subject); setEmailBody(step.body); setShowEmailEditor(true);
                                                }}>
                                                    <PenTool size={12} /> Edit Step
                                                </button>
                                                <button className="btn btn-ghost" style={{ fontSize: 12, color: 'var(--danger)' }} onClick={() => {
                                                    setSequenceSteps(prev => prev.filter(s => s.id !== step.id));
                                                }}>
                                                    <Trash2 size={12} /> Delete
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            className="btn btn-primary"
                            onClick={() => setShowAddStep(true)}
                            style={{ padding: '12px 24px', fontSize: 14, boxShadow: '0 0 15px var(--accent-glow)' }}
                        >
                            <Plus size={16} /> Add Sequence Step
                        </button>

                        {sequenceSteps.length === 0 && (
                            <div className="card" style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)', border: '1px dashed var(--border-strong)', marginTop: 24 }}>
                                <Link2 size={48} style={{ marginBottom: 16, opacity: 0.2, color: 'var(--accent-primary)' }} />
                                <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>No sequence steps yet</p>
                                <p style={{ fontSize: 13, marginTop: 8, maxWidth: 300, margin: '8px auto 0' }}>Click "Add Sequence Step" to define the emails that will be sent to leads.</p>
                            </div>
                        )}

                        {/* Editor Modal is unchanged structurally but adapts to globals.css */}
                        {showEmailEditor && (
                            <div className="modal-overlay" onClick={() => setShowEmailEditor(false)}>
                                <div className="modal-content fade-in" style={{ maxWidth: 800 }} onClick={e => e.stopPropagation()}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                                        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <Mail size={18} color="var(--accent-primary)" /> Email Step
                                        </h3>
                                        <button onClick={() => setShowEmailEditor(false)} className="btn-ghost" style={{ padding: 4, borderRadius: '50%' }}>
                                            <X size={18} />
                                        </button>
                                    </div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, padding: '12px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Subject:</span>
                                        <input
                                            value={emailSubject}
                                            onChange={e => setEmailSubject(e.target.value)}
                                            placeholder="Catchy subject line..."
                                            style={{ flex: 1, border: 'none', background: 'transparent', fontSize: 14, outline: 'none', color: 'var(--text-primary)' }}
                                            autoFocus
                                        />
                                    </div>

                                    <textarea
                                        value={emailBody}
                                        onChange={e => setEmailBody(e.target.value)}
                                        placeholder="Write your email content here. Use {{name}}, {{company}} as variables..."
                                        rows={12}
                                        style={{ width: '100%', resize: 'vertical', marginBottom: 24, fontSize: 14, lineHeight: 1.6 }}
                                    />

                                    <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                                        <button className="btn btn-secondary" onClick={() => setShowEmailEditor(false)}>Cancel</button>
                                        <button className="btn btn-primary" onClick={() => addSequenceStep('email')}>
                                            <Save size={14} /> Save Sequence Step
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div style={{ paddingTop: 20, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
                            <button className="btn btn-primary" onClick={() => saveConfigMut.mutate()} disabled={saveConfigMut.isPending}>
                                <Save size={14} /> {saveConfigMut.isPending ? 'Saving...' : 'Save Sequence Config'}
                            </button>
                        </div>
                    </div>
                )}

                {/* ═══════ SCHEDULE TAB ═══════ */}
                {activeTab === 'schedule' && (
                    <div className="fade-in" style={{ maxWidth: 680 }}>
                        <div className="card" style={{ padding: 32, marginBottom: 24 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                <CalendarDays size={20} color="var(--accent-primary)" />
                                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Sending Schedule</h3>
                            </div>
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>Define exactly when your outreach emails should be delivered to maximize open rates.</p>

                            <div style={{ display: 'flex', gap: 8, marginBottom: 32 }}>
                                {DAYS.map((d, i) => (
                                    <button
                                        key={d}
                                        onClick={() => toggleDay(i)}
                                        style={{
                                            padding: '8px 0', flex: 1, borderRadius: 'var(--radius-sm)', fontSize: 13, fontWeight: 600,
                                            border: selectedDays.includes(i) ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                            background: selectedDays.includes(i) ? 'transparent' : 'var(--bg-elevated)',
                                            color: selectedDays.includes(i) ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                            cursor: 'pointer', transition: 'all 0.2s',
                                            boxShadow: selectedDays.includes(i) ? 'inset 0 0 10px rgba(20, 184, 166, 0.1)' : 'none'
                                        }}
                                    >
                                        {d}
                                    </button>
                                ))}
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
                                <div>
                                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>From Time</label>
                                    <select value={scheduleStart} onChange={e => setScheduleStart(e.target.value)} style={{ width: '100%' }}>
                                        {['7:00 AM', '8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM'].map(t => <option key={t}>{t}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>To Time</label>
                                    <select value={scheduleEnd} onChange={e => setScheduleEnd(e.target.value)} style={{ width: '100%' }}>
                                        {['4:00 PM', '5:00 PM', '6:00 PM', '7:00 PM', '8:00 PM'].map(t => <option key={t}>{t}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div style={{ paddingTop: 20, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end' }}>
                                <button className="btn btn-primary" onClick={() => saveConfigMut.mutate()} disabled={saveConfigMut.isPending}>
                                    <Save size={14} /> {saveConfigMut.isPending ? 'Saving...' : 'Save Schedule'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ═══════ CONFIGURATIONS TAB ═══════ */}
                {activeTab === 'configurations' && (
                    <div className="fade-in" style={{ maxWidth: 680 }}>
                        <div className="card" style={{ padding: 32 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                <Settings2 size={20} color="var(--accent-primary)" />
                                <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Campaign Limits & Rules</h3>
                            </div>
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 32 }}>Protect your sender reputation by setting safe limits.</p>

                            <div style={{ marginBottom: 32, paddingBottom: 24, borderBottom: '1px solid var(--border-subtle)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                    <div>
                                        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Daily Max Emails Sent</div>
                                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Maximum number of emails to send per day across this campaign.</div>
                                    </div>
                                    <input
                                        type="number" value={dailyLimit} onChange={e => setDailyLimit(Number(e.target.value))}
                                        style={{ width: 100, textAlign: 'center', fontSize: 16, fontWeight: 600 }}
                                    />
                                </div>
                            </div>

                            <div style={{ marginBottom: 32, paddingBottom: 24, borderBottom: '1px solid var(--border-subtle)' }}>
                                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>Time Gap Between Emails</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>Introduce random delays to mimic human sending and avoid spam filters.</div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                                    <div className="card" style={{ padding: 16, border: '1px solid var(--border-subtle)', boxShadow: 'none' }}>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 12 }}>Base Delay</label>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                            <input type="number" value={timeGapMin} onChange={e => setTimeGapMin(Number(e.target.value))} style={{ width: '100%', textAlign: 'center' }} />
                                            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>min</span>
                                        </div>
                                    </div>
                                    <div className="card" style={{ padding: 16, border: '1px solid var(--border-subtle)', boxShadow: 'none' }}>
                                        <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 12 }}>Random Jitter</label>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                            <input type="number" value={timeGapRandom} onChange={e => setTimeGapRandom(Number(e.target.value))} style={{ width: '100%', textAlign: 'center' }} />
                                            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>min</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div style={{ marginBottom: 32 }}>
                                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Safety Rules</div>
                                <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'flex-start', gap: 12, border: '1px solid var(--border-subtle)', boxShadow: 'none', marginBottom: 12 }}>
                                    <input type="checkbox" defaultChecked id="stopOnReply" style={{ marginTop: 4, width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                                    <div>
                                        <label htmlFor="stopOnReply" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', cursor: 'pointer', display: 'block', marginBottom: 4 }}>
                                            Stop sequence on reply
                                        </label>
                                        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Automatically halt all automated follow-ups for a lead if they reply to any email.</p>
                                    </div>
                                </div>
                                <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'flex-start', gap: 12, border: '1px solid var(--border-subtle)', boxShadow: 'none' }}>
                                    <input type="checkbox" defaultChecked id="trackOpens" style={{ marginTop: 4, width: 16, height: 16, accentColor: 'var(--accent-primary)' }} />
                                    <div>
                                        <label htmlFor="trackOpens" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', cursor: 'pointer', display: 'block', marginBottom: 4 }}>
                                            Track email opens
                                        </label>
                                        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Embed a 1x1 tracking pixel. (Note: Can slightly affect deliverability).</p>
                                    </div>
                                </div>
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                <button className="btn btn-primary"><Save size={14} /> Save Config</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Import CSV Modal */}
            {showImport && (
                <div className="modal-overlay" onClick={() => setShowImport(false)}>
                    <div className="modal-content fade-in" onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Import Leads to Campaign</h3>
                            <button onClick={() => setShowImport(false)} className="btn-ghost" style={{ padding: 4, borderRadius: '50%' }}>
                                <X size={18} />
                            </button>
                        </div>
                        <div style={{
                            border: '2px dashed var(--border-strong)', borderRadius: 'var(--radius-md)', padding: 48,
                            textAlign: 'center', marginBottom: 24, cursor: 'pointer',
                            background: importFile ? 'rgba(16, 185, 129, 0.05)' : 'var(--bg-elevated)',
                            transition: 'all 0.2s',
                        }}>
                            <input type="file" accept=".csv" style={{ display: 'none' }} id="csvUpload"
                                onChange={e => setImportFile(e.target.files?.[0] || null)} />
                            <label htmlFor="csvUpload" style={{ cursor: 'pointer', width: '100%', display: 'block' }}>
                                {importFile ? (
                                    <CheckCircle2 size={36} color="var(--success)" style={{ marginBottom: 12, margin: '0 auto' }} />
                                ) : (
                                    <Upload size={36} color="var(--accent-primary)" style={{ marginBottom: 12, margin: '0 auto' }} />
                                )}
                                <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                                    {importFile ? importFile.name : 'Click to select CSV file'}
                                </p>
                                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>CSV must include "name" and "email" headers</p>
                            </label>
                        </div>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                            <button className="btn btn-secondary" onClick={() => setShowImport(false)}>Cancel</button>
                            <button
                                className="btn btn-primary"
                                onClick={() => importFile && importMut.mutate(importFile)}
                                disabled={!importFile || importMut.isPending}
                            >
                                {importMut.isPending ? 'Importing...' : 'Upload & Import'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
