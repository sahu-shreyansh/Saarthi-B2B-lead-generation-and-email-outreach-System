'use client';

import { useLeads, useCreateLead } from '@/hooks/useLeads';
import { useState, useMemo } from 'react';
import { Search, CheckSquare, Square, MoreHorizontal, TrendingUp, Plus, Zap, Loader2, X } from 'lucide-react';
import { useRouter } from 'next/navigation';

const STATUSES: Record<string, string> = {
    NEW: 'badge-blue',
    INTERESTED: 'badge-success',
    NOT_INTERESTED: 'badge-danger',
    MEETING_BOOKED: 'badge-cyan',
    CLOSED: 'badge-success',
    BOUNCED: 'badge-warning',
    UNSUBSCRIBED: 'badge-gray',
};

function ConfidenceBar({ value }: { value: number }) {
    const pct = Math.round((value || 0) * 100);
    const color = pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)';
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 48, height: 4, background: 'var(--bg-hover)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.3s' }} />
            </div>
            <span className="text-meta">{pct}%</span>
        </div>
    );
}

function RowSkeleton() {
    return (
        <tr>
            {[1, 2, 3, 4, 5, 6].map(i => (
                <td key={i}>
                    <div className="skeleton" style={{ height: 12, borderRadius: 4, width: i === 1 ? '80%' : i === 3 ? '90%' : '60%' }} />
                </td>
            ))}
        </tr>
    );
}

export default function LeadsPage() {
    const router = useRouter();
    const { data: leads = [], isLoading } = useLeads();
    const createLeadMutation = useCreateLead();

    // Add error handling to lead creation
    const handleAddLead = () => {
        createLeadMutation.mutate(newLead, {
            onSuccess: () => {
                setShowAddModal(false);
                setNewLead({ contact_name: '', contact_email: '', company_name: '' });
            },
            onError: (err: any) => {
                const msg = err.response?.data?.detail || err.message || 'Failed to add lead';
                alert(`Error: ${msg}`);
            }
        });
    };

    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [showAddModal, setShowAddModal] = useState(false);
    const [newLead, setNewLead] = useState({ contact_name: '', contact_email: '', company_name: '' });

    const filtered = useMemo(() => {
        const q = search.toLowerCase();
        return (leads as any[]).filter(lead =>
            !q ||
            lead.contact_name?.toLowerCase().includes(q) ||
            lead.contact_email?.toLowerCase().includes(q) ||
            lead.company_name?.toLowerCase().includes(q)
        );
    }, [leads, search]);


    const toggleSelect = (id: string) => {
        const next = new Set(selected);
        next.has(id) ? next.delete(id) : next.add(id);
        setSelected(next);
    };

    const allSelected = filtered.length > 0 && filtered.every((l: any) => selected.has(l.id));

    const toggleAll = () => {
        if (allSelected) {
            setSelected(new Set());
        } else {
            setSelected(new Set((filtered as any[]).map((l: any) => l.id)));
        }
    };

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-left">
                    <h1>Leads</h1>
                    <p>{(leads as any[]).length.toLocaleString()} total leads</p>
                </div>
                <div className="page-header-right flex items-center gap-2">
                    <div style={{ position: 'relative' }}>
                        <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
                        <input
                            className="input"
                            style={{ width: 220, paddingLeft: 32 }}
                            placeholder="Search leads…"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />
                    </div>
                    <button className="btn btn-secondary" onClick={() => router.push('/discovery')}>
                        <Zap size={14} className="text-blue-400" />
                        Discovery
                    </button>
                    <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
                        <Plus size={14} />
                        Add Lead
                    </button>
                </div>
            </div>

            {/* Bulk Bar */}
            {selected.size > 0 && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 16px', marginBottom: 12,
                    background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
                    borderRadius: 'var(--radius-md)', fontSize: 13,
                }}>
                    <TrendingUp size={14} color="var(--accent-primary)" />
                    <span style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>{selected.size} selected</span>
                    <button className="btn btn-secondary btn-sm">Export CSV</button>
                    <button className="btn btn-danger btn-sm">Delete</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => setSelected(new Set())}>Clear</button>
                </div>
            )}

            {/* Table */}
            <div className="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style={{ width: 40 }}>
                                <button onClick={toggleAll} className="btn btn-ghost btn-sm" style={{ padding: 0 }}>
                                    {allSelected
                                        ? <CheckSquare size={14} color="var(--accent-primary)" />
                                        : <Square size={14} color="var(--text-muted)" />}
                                </button>
                            </th>
                            <th>Name</th>
                            <th>Company</th>
                            <th>Email</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th style={{ width: 40 }}></th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading
                            ? [1, 2, 3, 4, 5, 6, 7, 8].map(i => <RowSkeleton key={i} />)
                            : filtered.length === 0
                                ? (
                                    <tr>
                                        <td colSpan={7}>
                                            <div className="empty-state">
                                                <p className="empty-state-text">No leads found yet.</p>
                                                <button
                                                    className="btn btn-primary mt-4"
                                                    onClick={() => router.push('/discovery')}
                                                >
                                                    Start Discovery
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                )
                                : (filtered as any[]).map((lead: any) => (
                                    <tr key={lead.id}>
                                        <td>
                                            <button onClick={() => toggleSelect(lead.id)} className="btn btn-ghost btn-sm" style={{ padding: 0 }}>
                                                {selected.has(lead.id)
                                                    ? <CheckSquare size={14} color="var(--accent-primary)" />
                                                    : <Square size={14} color="var(--text-muted)" />}
                                            </button>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{lead.contact_name || '—'}</td>
                                        <td className="text-secondary">{lead.company_name || '—'}</td>
                                        <td className="text-muted" style={{ fontFamily: 'monospace', fontSize: 12 }}>{lead.contact_email}</td>
                                        <td>
                                            <span className={`badge ${STATUSES[lead.status?.toUpperCase()] ?? 'badge-gray'}`}>
                                                {lead.status?.toUpperCase() || 'NEW'}
                                            </span>
                                        </td>
                                        <td>
                                            <ConfidenceBar value={lead.score || 0.1} />
                                        </td>
                                        <td>
                                            <button className="icon-btn">
                                                <MoreHorizontal size={14} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                        }
                    </tbody>
                </table>
            </div>

            {/* Add Lead Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="card-flat w-full max-w-md p-6 relative animate-in fade-in zoom-in duration-200">
                        <button
                            className="absolute right-4 top-4 text-gray-400 hover:text-white"
                            onClick={() => setShowAddModal(false)}
                        >
                            <X size={20} />
                        </button>

                        <h2 className="text-xl font-bold mb-6">Add New Lead</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1.5">Full Name</label>
                                <input
                                    className="input"
                                    placeholder="John Doe"
                                    value={newLead.contact_name}
                                    onChange={e => setNewLead({ ...newLead, contact_name: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1.5">Email Address</label>
                                <input
                                    className="input"
                                    placeholder="john@example.com"
                                    value={newLead.contact_email}
                                    onChange={e => setNewLead({ ...newLead, contact_email: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1.5">Company Name</label>
                                <input
                                    className="input"
                                    placeholder="Acme Corp"
                                    value={newLead.company_name}
                                    onChange={e => setNewLead({ ...newLead, company_name: e.target.value })}
                                />
                            </div>

                            <button
                                className="btn btn-primary w-full py-2.5 mt-4 flex items-center justify-center gap-2"
                                onClick={handleAddLead}
                                disabled={createLeadMutation.isPending || !newLead.contact_email}
                            >
                                {createLeadMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                                Add Lead
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
