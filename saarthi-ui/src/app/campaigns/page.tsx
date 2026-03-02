'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCampaigns, createCampaign, updateCampaign } from '@/lib/api';
import { useRouter } from 'next/navigation';
import {
    Plus, Play, Pause, Send, Reply,
    RefreshCw, Search, X, Clock, Users,
    BarChart3, Target, ChevronRight
} from 'lucide-react';

export default function CampaignsPage() {
    const qc = useQueryClient();
    const router = useRouter();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const { data: campaigns = [], isLoading } = useQuery({
        queryKey: ['campaigns'],
        queryFn: fetchCampaigns,
    });

    const createMut = useMutation({
        mutationFn: (name: string) => createCampaign(name),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ['campaigns'] });
            setShowCreate(false);
            setNewName('');
        },
        onError: (err: any) => alert(err?.response?.data?.detail || 'Failed'),
    });

    const toggleMut = useMutation({
        mutationFn: ({ id, status }: { id: string; status: string }) =>
            updateCampaign(id, { status: status === 'active' ? 'paused' : 'active' }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
    });

    const filtered = campaigns.filter((c: any) =>
        c.name?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="page-container fade-in">
            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">Campaigns</h1>
                    <p className="page-subtitle">Manage all active and paused outreach sequences</p>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <button className="btn btn-secondary" onClick={() => qc.invalidateQueries({ queryKey: ['campaigns'] })}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                    <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                        <Plus size={14} /> New Campaign
                    </button>
                </div>
            </div>

            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
                <div style={{ position: 'relative', width: 320 }}>
                    <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search campaigns by name..."
                        style={{ width: '100%', paddingLeft: 40, background: 'var(--bg-surface)' }}
                    />
                </div>

                <div style={{ display: 'flex', gap: 16 }}>
                    <div className="card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Total: <strong style={{ color: 'var(--text-primary)' }}>{campaigns.length}</strong></span>
                        <div style={{ width: 1, height: 16, background: 'var(--border-subtle)' }} />
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Active: <strong style={{ color: 'var(--accent-primary)' }}>{campaigns.filter((c: any) => c.status === 'active').length}</strong></span>
                    </div>
                </div>
            </div>

            {/* Campaign Grid */}
            {isLoading ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 60 }}>
                    <RefreshCw size={24} className="spin" style={{ marginBottom: 16, opacity: 0.5 }} />
                    <p>Loading campaigns...</p>
                </div>
            ) : filtered.length === 0 ? (
                <div className="card" style={{
                    textAlign: 'center', color: 'var(--text-muted)',
                    padding: 60, paddingBottom: 80,
                    border: '1px dashed var(--border-strong)',
                }}>
                    <Target size={48} style={{ marginBottom: 16, opacity: 0.2, color: 'var(--accent-primary)' }} />
                    <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {campaigns.length === 0 ? 'No campaigns yet' : 'No matching campaigns'}
                    </p>
                    <p style={{ fontSize: 13, marginTop: 8, maxWidth: 300, margin: '8px auto 24px' }}>
                        Create a campaign to define your sequence, add leads, and launch your automated outreach.
                    </p>
                    {campaigns.length === 0 && (
                        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
                            <Plus size={14} /> Create First Campaign
                        </button>
                    )}
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 20 }}>
                    {filtered.map((c: any, i: number) => (
                        <div
                            key={c.id}
                            className="card fade-in"
                            style={{ padding: 24, cursor: 'pointer', position: 'relative', overflow: 'hidden', animationDelay: `${i * 0.05}s` }}
                            onClick={() => router.push(`/campaigns/${c.id}`)}
                        >
                            {/* Active Glow Accent */}
                            {c.status === 'active' && (
                                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))', boxShadow: '0 0 10px var(--accent-glow)' }} />
                            )}

                            {/* Top Row */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                                <div>
                                    <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>{c.name}</h3>
                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                        <span className={`badge ${c.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                                            {c.status === 'active' ? 'Active' : 'Paused'}
                                        </span>
                                        <span style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                                            <Clock size={10} />
                                            {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                                        </span>
                                    </div>
                                </div>

                                <button
                                    onClick={(e) => { e.stopPropagation(); toggleMut.mutate({ id: c.id, status: c.status }); }}
                                    title={c.status === 'active' ? 'Pause' : 'Activate'}
                                    className="btn btn-ghost"
                                    style={{
                                        padding: 8, borderRadius: '50%',
                                        background: c.status === 'active' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                                        color: c.status === 'active' ? 'var(--warning)' : 'var(--success)'
                                    }}
                                >
                                    {c.status === 'active' ? <Pause size={16} /> : <Play size={16} style={{ marginLeft: 2 }} />}
                                </button>
                            </div>

                            {/* Stats Row */}
                            <div style={{
                                display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
                                gap: 12, marginTop: 20, paddingTop: 20,
                                borderTop: '1px solid var(--border-subtle)',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: 'rgba(20, 184, 166, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <Users size={16} color="var(--accent-primary)" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>Leads</div>
                                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{c.leads_count ?? 0}</div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: 'rgba(56, 189, 248, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <Send size={16} color="#38bdf8" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>Sent</div>
                                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{c.total_sent ?? 0}</div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-sm)', background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <Reply size={16} color="var(--success)" />
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>Reply Rate</div>
                                        <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{c.reply_rate ?? 0}%</div>
                                    </div>
                                </div>
                            </div>

                            <div className="hover-arrow" style={{ position: 'absolute', bottom: 16, right: 16, opacity: 0, transition: 'opacity 0.2s' }}>
                                <ChevronRight size={16} color="var(--text-muted)" />
                            </div>
                        </div>
                    ))}
                    <style>{`.card:hover .hover-arrow { opacity: 1 !important; }`}</style>
                </div>
            )}

            {/* Create Campaign Modal */}
            {showCreate && (
                <div className="modal-overlay" onClick={() => setShowCreate(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Create New Campaign</h3>
                            <button onClick={() => setShowCreate(false)} className="btn-ghost" style={{ padding: 4, borderRadius: '50%' }}>
                                <X size={18} />
                            </button>
                        </div>

                        <div style={{ marginBottom: 24 }}>
                            <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                                Campaign Name
                            </label>
                            <input
                                value={newName}
                                onChange={e => setNewName(e.target.value)}
                                placeholder="e.g. Q4 SaaS Founders Outreach"
                                style={{ width: '100%' }}
                                autoFocus
                                onKeyDown={e => e.key === 'Enter' && newName.trim() && createMut.mutate(newName.trim())}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                            <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                            <button
                                className="btn btn-primary"
                                onClick={() => newName.trim() && createMut.mutate(newName.trim())}
                                disabled={!newName.trim() || createMut.isPending}
                            >
                                {createMut.isPending ? 'Creating...' : 'Create Campaign'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
