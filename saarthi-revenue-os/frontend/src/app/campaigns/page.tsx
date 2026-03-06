'use client';

import { useCampaigns, useCreateCampaign, useStartCampaign, usePauseCampaign } from '@/hooks/useCampaigns';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Play, Pause, Plus, MoreHorizontal } from 'lucide-react';

const statusStyle: Record<string, string> = {
    active: 'badge-success',
    paused: 'badge-warning',
    completed: 'badge-gray',
    draft: 'badge-blue',
};

function CampaignSkeleton() {
    return (
        <div className="card-flat" style={{ padding: 20, marginBottom: 10 }}>
            <div className="flex items-center justify-between">
                <div style={{ flex: 1 }}>
                    <div className="skeleton" style={{ height: 14, width: '35%', marginBottom: 8 }} />
                    <div className="skeleton" style={{ height: 10, width: '20%' }} />
                </div>
                <div className="skeleton" style={{ height: 28, width: 80, borderRadius: 6 }} />
            </div>
        </div>
    );
}

export default function CampaignsPage() {
    const router = useRouter();
    const { data: campaigns = [], isLoading } = useCampaigns();

    const startMutation = useStartCampaign();
    const pauseMutation = usePauseCampaign();
    const createMutation = useCreateCampaign();

    const handleStartPause = (c: any) => {
        const mutation = c.status === 'active' ? pauseMutation : startMutation;
        mutation.mutate(c.id, {
            onError: (err: any) => {
                const msg = err.response?.data?.detail || err.message || `Failed to ${c.status === 'active' ? 'pause' : 'start'} campaign`;
                alert(`Error: ${msg}`);
            }
        });
    };

    const handleCreate = () => {
        createMutation.mutate({ name: "Live AI Test - " + Math.floor(Math.random() * 1000) }, {
            onError: (err: any) => {
                const msg = err.response?.data?.detail || err.message || 'Failed to create campaign';
                alert(`Error: ${msg}`);
            }
        });
    };

    const [activeTab, setActiveTab] = useState<'all' | 'active' | 'paused'>('all');

    const filtered = (campaigns as any[]).filter(c => {
        if (activeTab === 'active') return c.status === 'active';
        if (activeTab === 'paused') return c.status === 'paused';
        return true;
    });

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-left">
                    <h1>Campaigns</h1>
                    <p>{(campaigns as any[]).length} total campaigns</p>
                </div>
                <div className="page-header-right">
                    <button
                        className="btn btn-primary"
                        onClick={handleCreate}
                        disabled={createMutation.isPending}
                    >
                        <Plus size={14} />
                        {createMutation.isPending ? 'Creating...' : 'New Campaign'}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="tab-bar">
                {(['all', 'active', 'paused'] as const).map(t => (
                    <button
                        key={t}
                        className={`tab${activeTab === t ? ' active' : ''}`}
                        onClick={() => setActiveTab(t)}
                    >
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                ))}
            </div>

            {/* Campaign Cards */}
            {isLoading
                ? [1, 2, 3].map(i => <CampaignSkeleton key={i} />)
                : filtered.length === 0
                    ? (
                        <div className="empty-state">
                            <p className="empty-state-text">No campaigns yet.</p>
                            <button
                                className="btn btn-primary"
                                onClick={handleCreate}
                                disabled={createMutation.isPending}
                            >
                                <Plus size={14} />
                                {createMutation.isPending ? 'Creating...' : 'Create Campaign'}
                            </button>
                        </div>
                    )
                    : filtered.map((c: any) => (
                        <div key={c.id} className="card-flat" style={{ padding: 20, marginBottom: 10 }}>
                            <div className="flex items-center justify-between">
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div className="flex items-center gap-1" style={{ marginBottom: 6, gap: 10 }}>
                                        <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                                            {c.name}
                                        </span>
                                        <span className={`badge ${statusStyle[c.status] ?? 'badge-gray'}`}>
                                            {c.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1" style={{ gap: 20 }}>
                                        <span className="text-meta">
                                            Limit: {c.daily_limit ?? '—'}/day
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1" style={{ gap: 8 }}>
                                    <button
                                        className={`btn ${c.status === 'active' ? 'btn-secondary' : 'btn-primary'} btn-sm`}
                                        disabled={startMutation.isPending || pauseMutation.isPending}
                                        onClick={() => handleStartPause(c)}
                                    >
                                        {c.status === 'active' ? <Pause size={13} /> : <Play size={13} />}
                                        {c.status === 'active' ? 'Pause' : 'Start'}
                                    </button>
                                    <button className="icon-btn">
                                        <MoreHorizontal size={15} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))
            }
        </div>
    );
}
