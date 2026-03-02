'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchLeads } from '@/lib/api';
import { Users, Mail, Building2, Target, MoveRight } from 'lucide-react';

const STAGES = [
    { key: 'NEW', label: 'Lead', color: 'var(--accent-primary)', bg: 'rgba(20, 184, 166, 0.1)' },
    { key: 'IN_SEQUENCE', label: 'Contacted', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' },
    { key: 'REPLIED', label: 'Replied', color: 'var(--success)', bg: 'rgba(16, 185, 129, 0.1)' },
    { key: 'CLOSED', label: 'Closed', color: 'var(--text-secondary)', bg: 'var(--bg-elevated)' },
];

export default function DealPipelinePage() {
    const { data: leads = [], isLoading } = useQuery({
        queryKey: ['leads'],
        queryFn: () => fetchLeads({}),
    });

    // Group leads by status into pipeline stages
    const grouped: Record<string, any[]> = {};
    for (const stage of STAGES) {
        grouped[stage.key] = leads.filter((l: any) => l.status === stage.key);
    }

    const totalLeads = leads.length;

    return (
        <div className="page-container fade-in" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '100vh', paddingBottom: 24 }}>
            <div className="page-header" style={{ marginBottom: 20 }}>
                <div>
                    <h1 className="page-title">Deal Pipeline</h1>
                    <p className="page-subtitle">Track prospects across their entire lifecycle ({totalLeads} total)</p>
                </div>
            </div>

            {isLoading && (
                <div className="card" style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <Target size={32} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
                    <p>Loading pipeline data...</p>
                </div>
            )}

            <div style={{
                display: 'grid', gridTemplateColumns: `repeat(${STAGES.length}, 1fr)`,
                gap: 16, flex: 1, overflow: 'hidden', minHeight: 0
            }}>
                {STAGES.map((stage, i) => (
                    <div key={stage.key} className="fade-in" style={{
                        background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', padding: '16px',
                        display: 'flex', flexDirection: 'column', border: '1px solid var(--border-subtle)',
                        height: '100%', animationDelay: `${i * 0.05}s`
                    }}>
                        {/* Column header */}
                        <div style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '12px 16px', borderRadius: 'var(--radius-sm)', marginBottom: 16,
                            background: stage.bg, border: `1px solid ${stage.color}30`
                        }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: stage.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{stage.label}</span>
                            <span style={{
                                fontSize: 12, fontWeight: 700, color: stage.color,
                                background: 'var(--bg-surface)', padding: '2px 8px', borderRadius: 'var(--radius-full)',
                                border: `1px solid ${stage.color}40`, boxShadow: `0 0 10px ${stage.color}20`
                            }}>
                                {grouped[stage.key]?.length || 0}
                            </span>
                        </div>

                        {/* Cards Container */}
                        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 4, margin: '0 -4px 0 0', paddingLeft: 4 }}>
                            {!grouped[stage.key] || grouped[stage.key].length === 0 ? (
                                <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-md)', background: 'var(--bg-elevated)' }}>
                                    No leads in this stage
                                </div>
                            ) : (
                                grouped[stage.key].map((lead: any, idx: number) => (
                                    <div key={lead.id} className="card" style={{ padding: '16px', cursor: 'grab', position: 'relative', overflow: 'hidden', animationDelay: `${(i * 0.1) + (idx * 0.02)}s` }}
                                        onMouseOver={e => e.currentTarget.style.borderColor = stage.color}
                                        onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}>

                                        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: stage.color }} />

                                        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, paddingLeft: 8 }}>
                                            {lead.name}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4, paddingLeft: 8 }}>
                                            <Mail size={12} /> <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.email}</span>
                                        </div>
                                        {lead.company && (
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)', paddingLeft: 8 }}>
                                                <Building2 size={12} /> <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{lead.company}</span>
                                            </div>
                                        )}
                                        {lead.campaign && (
                                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 4, paddingLeft: 8 }}>
                                                <Target size={10} /> {lead.campaign}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                ))}
            </div>
            <style>{`.page-container ::-webkit-scrollbar { width: 4px; } .page-container ::-webkit-scrollbar-track { background: transparent; } .page-container ::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 4px; }`}</style>
        </div>
    );
}
