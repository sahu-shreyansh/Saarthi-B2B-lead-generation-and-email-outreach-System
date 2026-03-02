'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchLeads, fetchCampaigns, sendEmail } from '@/lib/api';
import {
    Mail, Plus, Trash2, Eye, Send, Clock, Variable, Wand2, ArrowRight
} from 'lucide-react';

const VARIABLES = [
    { key: '{{first_name}}', label: 'First Name' },
    { key: '{{last_name}}', label: 'Last Name' },
    { key: '{{company}}', label: 'Company' },
    { key: '{{title}}', label: 'Title' },
    { key: '{{industry}}', label: 'Industry' },
    { key: '{{location}}', label: 'Location' },
    { key: '{{sender_name}}', label: 'Sender Name' },
];

interface SequenceStep {
    id: number; type: 'email' | 'delay'; subject: string; body: string; delayDays: number;
}

const DEFAULT_TEMPLATES = [
    {
        name: 'Cold Intro',
        subject: 'Quick question for {{first_name}}',
        body: `Hi {{first_name}},\n\nI noticed {{company}} is doing great work in the {{industry}} space. Given your role as {{title}}, I thought you might find this relevant.\n\nWe help companies like {{company}} increase their outbound reply rates by 3x through AI-personalized email outreach.\n\nWould you be open to a 15-minute call this week?\n\nBest,\n{{sender_name}}`,
    },
    {
        name: 'Follow-up #1',
        subject: 'Re: Quick question for {{first_name}}',
        body: `Hi {{first_name}},\n\nJust wanted to follow up on my previous email. I understand things get busy at {{company}}.\n\nIf email outreach optimization is on your radar, I'd love to share how we've helped similar {{industry}} companies.\n\nLet me know if you'd find a brief chat useful.\n\nBest,\n{{sender_name}}`,
    },
    {
        name: 'Break-up',
        subject: 'Re: Quick question for {{first_name}}',
        body: `Hi {{first_name}},\n\nI don't want to be a bother — this will be my last follow-up.\n\nIf improving outbound performance at {{company}} becomes a priority, feel free to reach out anytime.\n\nWishing you and the team all the best.\n\n{{sender_name}}`,
    },
];

export default function OutreachPage() {
    const qc = useQueryClient();
    const [sequence, setSequence] = useState<SequenceStep[]>([
        { id: 1, type: 'email', subject: DEFAULT_TEMPLATES[0].subject, body: DEFAULT_TEMPLATES[0].body, delayDays: 0 },
        { id: 2, type: 'delay', subject: '', body: '', delayDays: 3 },
        { id: 3, type: 'email', subject: DEFAULT_TEMPLATES[1].subject, body: DEFAULT_TEMPLATES[1].body, delayDays: 0 },
        { id: 4, type: 'delay', subject: '', body: '', delayDays: 5 },
        { id: 5, type: 'email', subject: DEFAULT_TEMPLATES[2].subject, body: DEFAULT_TEMPLATES[2].body, delayDays: 0 },
    ]);

    const [activeStepId, setActiveStepId] = useState(1);
    const [showPreview, setShowPreview] = useState(false);
    const [showVars, setShowVars] = useState(false);
    const [showTemplates, setShowTemplates] = useState(false);
    const [showLaunch, setShowLaunch] = useState(false);
    const [selectedCampaign, setSelectedCampaign] = useState('');
    const [sendingStatus, setSendingStatus] = useState<string>('');
    const [sentCount, setSentCount] = useState(0);

    const { data: campaigns = [] } = useQuery({ queryKey: ['campaigns'], queryFn: fetchCampaigns });
    const { data: leads = [] } = useQuery({
        queryKey: ['leads', selectedCampaign],
        queryFn: () => fetchLeads(selectedCampaign ? { campaign_id: selectedCampaign } : {}),
        enabled: !!selectedCampaign,
    });

    const activeStep = sequence.find(s => s.id === activeStepId && s.type === 'email');
    const emailSteps = sequence.filter(s => s.type === 'email');

    const updateStep = (id: number, updates: Partial<SequenceStep>) => {
        setSequence(prev => prev.map(s => s.id === id ? { ...s, ...updates } : s));
    };

    const addEmailStep = () => {
        const newDelay: SequenceStep = { id: Date.now(), type: 'delay', subject: '', body: '', delayDays: 3 };
        const newEmail: SequenceStep = { id: Date.now() + 1, type: 'email', subject: '', body: '', delayDays: 0 };
        setSequence(prev => [...prev, newDelay, newEmail]);
        setActiveStepId(newEmail.id);
    };

    const removeStep = (id: number) => {
        setSequence(prev => {
            const idx = prev.findIndex(s => s.id === id);
            const newSeq = [...prev];
            if (idx > 0 && newSeq[idx - 1].type === 'delay') newSeq.splice(idx - 1, 2);
            else newSeq.splice(idx, 1);
            return newSeq;
        });
        if (activeStepId === id) setActiveStepId(sequence[0]?.id || 0);
    };

    const insertVariable = (varKey: string) => {
        if (!activeStep) return;
        updateStep(activeStep.id, { body: activeStep.body + varKey });
    };

    const personalizeForLead = (text: string, lead: any) => {
        const user = typeof window !== 'undefined' ? JSON.parse(localStorage.getItem('saarthi_user') || '{}') : {};
        const first = (lead.name || '').split(' ')[0] || '';
        const last = (lead.name || '').split(' ').slice(1).join(' ') || '';
        return text
            .replaceAll('{{first_name}}', first).replaceAll('{{last_name}}', last)
            .replaceAll('{{company}}', lead.company || '').replaceAll('{{title}}', lead.title || '')
            .replaceAll('{{industry}}', '').replaceAll('{{location}}', lead.location || '')
            .replaceAll('{{sender_name}}', user.full_name || user.email || 'Me');
    };

    const previewLead = { name: 'Priya Sharma', company: 'TechVenture', title: 'VP of Sales', location: 'Mumbai' };
    const previewText = (text: string) => personalizeForLead(text, previewLead);

    const launchSequence = async () => {
        if (!selectedCampaign) { alert('Please select a campaign'); return; }
        const newLeads = leads.filter((l: any) => l.status === 'NEW');
        if (newLeads.length === 0) { alert('No NEW leads in this campaign to send to'); return; }
        setSendingStatus('Sending step 1...');
        setSentCount(0);
        const firstEmail = emailSteps[0];
        if (!firstEmail) return;
        let count = 0;
        for (const lead of newLeads) {
            try {
                const subject = personalizeForLead(firstEmail.subject, lead);
                const body = personalizeForLead(firstEmail.body, lead);
                await sendEmail(lead.id, subject, body);
                count++;
                setSentCount(count);
                setSendingStatus(`Sent ${count}/${newLeads.length}...`);
            } catch (err: any) {
                if (err?.response?.status === 402) { alert('Monthly email limit reached.'); break; }
                console.error('Send failed for', lead.email, err);
            }
        }
        setSendingStatus(`Done! Sent ${count} emails.`);
        qc.invalidateQueries({ queryKey: ['leads'] });
        setTimeout(() => { setSendingStatus(''); setShowLaunch(false); }, 2000);
    };

    return (
        <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
            {/* Left: Sequence Timeline */}
            <div style={{
                width: 300, minWidth: 300, background: 'var(--bg-surface)', borderRight: '1px solid var(--border-subtle)',
                display: 'flex', flexDirection: 'column', zIndex: 5,
            }}>
                <div style={{ padding: '24px 24px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>Visual Sequence</h2>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{emailSteps.length} email steps</p>
                </div>

                <div style={{ flex: 1, padding: '24px', overflow: 'auto', position: 'relative' }}>
                    {/* Timeline vertical bar */}
                    <div style={{ position: 'absolute', top: 32, bottom: 32, left: 40, width: 2, background: 'var(--border-strong)', zIndex: 0 }} />

                    {sequence.map(step => {
                        if (step.type === 'delay') {
                            return (
                                <div key={step.id} style={{ display: 'flex', alignItems: 'center', marginBottom: 20, paddingLeft: 8, position: 'relative', zIndex: 1 }}>
                                    <div style={{ width: 16, height: 16, borderRadius: '50%', background: 'var(--bg-surface)', border: '2px solid var(--warning)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1 }}>
                                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--warning)' }} />
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16, background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '6px 12px', borderRadius: 'var(--radius-sm)' }}>
                                        <Clock size={12} color="var(--warning)" />
                                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--warning)' }}>Wait</span>
                                        <input
                                            type="number" min="1" max="30" value={step.delayDays}
                                            onChange={e => updateStep(step.id, { delayDays: parseInt(e.target.value) || 1 })}
                                            style={{
                                                width: 36, padding: '2px 4px', border: '1px solid var(--border-subtle)',
                                                background: 'var(--bg-elevated)', color: 'var(--text-primary)',
                                                borderRadius: 4, fontSize: 12, textAlign: 'center', outline: 'none',
                                            }}
                                        />
                                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--warning)' }}>days</span>
                                    </div>
                                </div>
                            );
                        }

                        const stepNum = emailSteps.findIndex(s => s.id === step.id) + 1;
                        const isActive = step.id === activeStepId;

                        return (
                            <div key={step.id} onClick={() => setActiveStepId(step.id)} className="card" style={{
                                display: 'flex', alignItems: 'flex-start', gap: 12,
                                padding: '16px', cursor: 'pointer', position: 'relative', zIndex: 1,
                                border: isActive ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                background: isActive ? 'rgba(20, 184, 166, 0.05)' : 'var(--bg-elevated)',
                                boxShadow: isActive ? '0 0 15px rgba(20, 184, 166, 0.1)' : 'none',
                                marginBottom: 20, transition: 'all 0.2s', marginLeft: 32,
                            }}>
                                <div style={{
                                    position: 'absolute', left: -24, top: 16, width: 32, height: 32, borderRadius: '50%',
                                    background: isActive ? 'var(--accent-primary)' : 'var(--bg-surface)',
                                    border: isActive ? 'none' : '2px solid var(--border-strong)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2,
                                    fontSize: 12, fontWeight: 700, color: isActive ? '#fff' : 'var(--text-muted)',
                                    boxShadow: isActive ? '0 0 10px var(--accent-glow)' : 'none'
                                }}>
                                    {isActive ? <Mail size={14} color="#000" /> : stepNum}
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: 14, fontWeight: 700, color: isActive ? 'var(--accent-primary)' : 'var(--text-primary)', marginBottom: 4 }}>Email {stepNum}</div>
                                    <div style={{
                                        fontSize: 12, color: 'var(--text-secondary)',
                                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const,
                                    }}>
                                        {step.subject || 'No subject'}
                                    </div>
                                </div>
                                {emailSteps.length > 1 && (
                                    <button onClick={e => { e.stopPropagation(); removeStep(step.id); }} className="btn-ghost"
                                        style={{ padding: 6, color: 'var(--danger)', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.05)' }}>
                                        <Trash2 size={14} />
                                    </button>
                                )}
                            </div>
                        );
                    })}

                    <button onClick={addEmailStep} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        gap: 8, width: 'calc(100% - 32px)', padding: '12px', borderRadius: 'var(--radius-md)',
                        border: '2px dashed var(--border-strong)', background: 'transparent',
                        color: 'var(--text-secondary)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                        marginLeft: 32, transition: 'all 0.2s',
                    }}
                        onMouseOver={e => { e.currentTarget.style.color = 'var(--accent-primary)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                        onMouseOut={e => { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.borderColor = 'var(--border-strong)'; }}>
                        <Plus size={16} /> Add Next Step
                    </button>
                </div>
            </div>

            {/* Right: Email Editor */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-base)' }}>
                {/* Toolbar */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '20px 32px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-surface)',
                }}>
                    <div style={{ display: 'flex', gap: 12 }}>
                        {[
                            { show: showVars, toggle: () => { setShowVars(!showVars); setShowTemplates(false); }, icon: Variable, label: 'Variables' },
                            { show: showTemplates, toggle: () => { setShowTemplates(!showTemplates); setShowVars(false); }, icon: Wand2, label: 'Templates' },
                            { show: showPreview, toggle: () => setShowPreview(!showPreview), icon: Eye, label: showPreview ? 'Edit' : 'Preview' },
                        ].map(btn => (
                            <button key={btn.label} onClick={btn.toggle} className={`btn ${btn.show ? 'btn-primary' : 'btn-secondary'}`}
                                style={{ fontSize: 13, padding: '8px 16px' }}>
                                <btn.icon size={14} /> {btn.label}
                            </button>
                        ))}
                    </div>
                    <div>
                        <button className="btn btn-primary" onClick={() => setShowLaunch(true)} style={{ padding: '8px 24px', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', border: 'none', color: '#000' }}>
                            <Send size={14} /> Launch Sequence
                        </button>
                    </div>
                </div>

                {/* Drawers */}
                {/* Variables drawer */}
                <div style={{ maxHeight: showVars ? 200 : 0, overflow: 'hidden', transition: 'max-height 0.3s ease', background: 'var(--bg-elevated)', borderBottom: showVars ? '1px solid var(--border-subtle)' : 'none' }}>
                    <div style={{ padding: '24px 32px' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Click to Insert
                        </div>
                        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                            {VARIABLES.map(v => (
                                <button key={v.key} onClick={() => insertVariable(v.key)} style={{
                                    padding: '8px 16px', borderRadius: 'var(--radius-sm)',
                                    border: '1px solid rgba(20, 184, 166, 0.3)', background: 'rgba(20, 184, 166, 0.05)',
                                    color: 'var(--accent-primary)', fontSize: 13, fontWeight: 600,
                                    cursor: 'pointer', fontFamily: 'monospace',
                                    transition: 'all 0.2s',
                                }}>
                                    {v.label}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Templates drawer */}
                <div style={{ maxHeight: showTemplates ? 300 : 0, overflow: 'hidden', transition: 'max-height 0.3s ease', background: 'var(--bg-elevated)', borderBottom: showTemplates ? '1px solid var(--border-subtle)' : 'none' }}>
                    <div style={{ padding: '24px 32px' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Quick Templates
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                            {DEFAULT_TEMPLATES.map(t => (
                                <div key={t.name} onClick={() => { if (activeStep) updateStep(activeStep.id, { subject: t.subject, body: t.body }); setShowTemplates(false); }}
                                    className="card" style={{ padding: '16px', cursor: 'pointer', border: '1px solid var(--border-subtle)', boxShadow: 'none' }}
                                    onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                                    onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}>
                                    <div style={{ fontWeight: 700, marginBottom: 8, fontSize: 14, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        {t.name} <ArrowRight size={14} color="var(--accent-primary)" />
                                    </div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.subject}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Editor Content */}
                <div style={{ flex: 1, overflow: 'auto', padding: '32px 48px', position: 'relative' }}>
                    {activeStep ? (
                        showPreview ? (
                            <div className="card fade-in" style={{
                                maxWidth: 760, margin: '0 auto', padding: '48px 56px',
                                borderTop: '4px solid var(--accent-primary)'
                            }}>
                                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '1px' }}>PREVIEW FOR {previewLead.name}</div>
                                <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 32, color: 'var(--text-primary)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 24 }}>
                                    {previewText(activeStep.subject) || '(No subject)'}
                                </div>
                                <div style={{ fontSize: 16, lineHeight: 1.8, whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
                                    {previewText(activeStep.body) || '(Empty body)'}
                                </div>
                            </div>
                        ) : (
                            <div className="fade-in" style={{ maxWidth: 840, margin: '0 auto' }}>
                                <div style={{ marginBottom: 24 }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: 10 }}>Subject Line</label>
                                    <input type="text" value={activeStep.subject}
                                        onChange={e => updateStep(activeStep.id, { subject: e.target.value })}
                                        placeholder="Enter an engaging subject line..."
                                        style={{ width: '100%', fontSize: 16, padding: '16px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', borderRadius: 'var(--radius-md)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)' }} />
                                </div>
                                <div style={{ position: 'relative' }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: 10 }}>Email Body</label>
                                    <textarea value={activeStep.body}
                                        onChange={e => updateStep(activeStep.id, { body: e.target.value })}
                                        placeholder="Write your message here... Use variables to personalize." rows={18}
                                        style={{ width: '100%', fontSize: 15, lineHeight: 1.8, resize: 'vertical', fontFamily: "'Inter', sans-serif", padding: '20px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', borderRadius: 'var(--radius-md)', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.1)' }} />
                                </div>
                                <div style={{
                                    marginTop: 24, padding: '16px 20px', borderRadius: 'var(--radius-sm)',
                                    background: 'rgba(20, 184, 166, 0.05)', border: '1px solid rgba(20, 184, 166, 0.2)',
                                    fontSize: 13, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 12
                                }}>
                                    <Wand2 size={18} color="var(--accent-primary)" />
                                    <span>
                                        Aim for short, punchy paragraphs. Emails between 50-125 words typically see the highest response rates.
                                    </span>
                                </div>
                            </div>
                        )
                    ) : (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', paddingTop: 100 }}>
                            <Mail size={48} style={{ margin: '0 auto 24px', opacity: 0.2 }} />
                            <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>Select a step</h3>
                            <p style={{ fontSize: 14 }}>Choose an email step from the timeline to start editing.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Launch Modal */}
            {showLaunch && (
                <div className="modal-overlay" onClick={() => !sendingStatus && setShowLaunch(false)}>
                    <div className="modal-content fade-in" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgba(20, 184, 166, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Send size={20} color="var(--accent-primary)" />
                            </div>
                            <h3 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>Launch Sequence</h3>
                        </div>

                        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.6 }}>
                            You are about to start sending <strong>Email 1</strong> to all NEW leads in your selected campaign.
                        </p>

                        <div style={{ marginBottom: 24 }}>
                            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>Target Campaign</label>
                            <select value={selectedCampaign} onChange={e => setSelectedCampaign(e.target.value)} style={{ width: '100%', padding: '12px', background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)', borderRadius: 'var(--radius-sm)' }}>
                                <option value="">Select a campaign...</option>
                                {campaigns.map((c: any) => <option key={c.id} value={c.id}>{c.name} ({c.leads_count} leads)</option>)}
                            </select>
                        </div>

                        {selectedCampaign && (
                            <div style={{
                                padding: '16px', borderRadius: 'var(--radius-sm)',
                                background: 'rgba(20, 184, 166, 0.1)', border: '1px solid rgba(20, 184, 166, 0.2)',
                                fontSize: 14, color: 'var(--text-primary)', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12
                            }}>
                                <Mail size={16} color="var(--accent-primary)" />
                                <span><strong style={{ color: 'var(--accent-primary)', fontSize: 16 }}>{leads.filter((l: any) => l.status === 'NEW').length}</strong> leads are ready to be contacted.</span>
                            </div>
                        )}

                        {sendingStatus && (
                            <div style={{
                                padding: '16px', borderRadius: 'var(--radius-sm)',
                                background: sendingStatus.startsWith('Done') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                                border: `1px solid ${sendingStatus.startsWith('Done') ? 'var(--success)' : 'var(--warning)'}`,
                                color: sendingStatus.startsWith('Done') ? 'var(--success)' : 'var(--warning)',
                                fontSize: 14, fontWeight: 600, marginBottom: 24, textAlign: 'center'
                            }}>
                                {sendingStatus}
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', paddingTop: 24, borderTop: '1px solid var(--border-subtle)' }}>
                            <button className="btn btn-secondary" onClick={() => !sendingStatus && setShowLaunch(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={launchSequence}
                                disabled={!!sendingStatus || !selectedCampaign}
                                style={{ pointerEvents: sendingStatus ? 'none' : 'auto', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', border: 'none', color: '#000' }}>
                                <Send size={14} /> {sendingStatus ? 'Sending Out...' : 'Confirm Launch'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
