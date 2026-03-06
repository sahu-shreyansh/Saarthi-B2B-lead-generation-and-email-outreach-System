'use client';

import { useState } from 'react';
import { useMeetings, useCreateMeeting, useUpdateMeeting } from '@/hooks/useMeetings';
import { CalendarDays, Clock, Video, User, Plus, Search, MoreHorizontal } from 'lucide-react';

const STATUS_FILTERS = ['all', 'scheduled', 'completed', 'canceled'];

export default function MeetingsPage() {
    const [filter, setFilter] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');

    const { data: meetings = [], isLoading } = useMeetings();
    const createMut = useCreateMeeting();
    const updateMut = useUpdateMeeting();

    const filtered = (meetings as any[]).filter(m => {
        if (filter !== 'all' && m.status !== filter) return false;
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            return m.title?.toLowerCase().includes(q) || m.lead_name?.toLowerCase().includes(q);
        }
        return true;
    });

    const getStatusTheme = (status: string) => {
        switch (status) {
            case 'scheduled': return 'badge-blue';
            case 'completed': return 'badge-success';
            case 'canceled': return 'badge-danger';
            default: return 'badge-gray';
        }
    };

    return (
        <div>
            {/* Header */}
            <div className="page-header">
                <div className="page-header-left">
                    <h1>Meetings</h1>
                    <p>Manage scheduled calls with prospects</p>
                </div>
                <div className="page-header-right">
                    <button className="btn btn-primary" onClick={() => alert("Calendar connection required to generate new meeting links inline.")}>
                        <Plus size={14} /> New Meeting
                    </button>
                </div>
            </div>

            {/* Filters & Search */}
            <div className="flex items-center justify-between mb-4">
                <div className="tab-bar m-0">
                    {STATUS_FILTERS.map(f => (
                        <button
                            key={f}
                            className={`tab${filter === f ? ' active' : ''}`}
                            onClick={() => setFilter(f)}
                            style={{ textTransform: 'capitalize' }}
                        >
                            {f}
                        </button>
                    ))}
                </div>
                <div className="relative" style={{ width: 260 }}>
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" style={{ pointerEvents: 'none' }} />
                    <input
                        className="input w-full"
                        style={{ paddingLeft: 34 }}
                        placeholder="Search meetings..."
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            {/* Content */}
            {isLoading ? (
                <div className="p-12 text-center text-muted">Loading calendar events...</div>
            ) : filtered.length === 0 ? (
                <div className="card-flat p-12 text-center flex-col items-center">
                    <CalendarDays size={48} className="text-secondary opacity-30 mb-4 mx-auto" />
                    <h3 className="text-lg font-bold mb-1">No meetings found</h3>
                    <p className="text-meta">
                        {searchQuery ? "Try adjusting your search filters." : "When leads book meetings via AI, they will appear here."}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                    {filtered.map(meet => (
                        <div key={meet.id} className="card-flat p-5 fade-in hover:border-focus transition-colors">
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h4 className="font-bold text-primary truncate pr-2">{meet.title}</h4>
                                    <span className={`badge ${getStatusTheme(meet.status)} mt-2 inline-block`}>
                                        {meet.status?.toUpperCase() || 'SCHEDULED'}
                                    </span>
                                </div>
                                <button className="icon-btn shrink-0"><MoreHorizontal size={16} /></button>
                            </div>

                            <div className="flex-col gap-2 mb-4">
                                <div className="flex items-center gap-2 text-sm text-secondary">
                                    <Clock size={14} className="text-muted" />
                                    <span>{new Date(meet.scheduled_time || new Date()).toLocaleString()} ({meet.duration_minutes || 30}m)</span>
                                </div>
                                <div className="flex items-center gap-2 text-sm text-secondary">
                                    <User size={14} className="text-muted" />
                                    <span>{meet.lead_name || 'Prospect'} ({meet.lead_email || '—'})</span>
                                </div>
                            </div>

                            <div className="flex gap-2 pt-4 border-t border-border mt-auto">
                                <button
                                    className="btn btn-primary flex-1 bg-blue-600/10 text-blue-500 border border-blue-600/20 hover:bg-blue-600/20"
                                    onClick={() => window.open(meet.meeting_link || 'https://meet.google.com', '_blank')}
                                >
                                    <Video size={14} /> Join Call
                                </button>
                                {meet.status === 'scheduled' && (
                                    <button
                                        className="btn btn-secondary flex-1 hover:border-danger hover:text-danger"
                                        onClick={() => {
                                            if (confirm('Cancel this meeting?')) {
                                                updateMut.mutate({ id: meet.id, status: 'canceled' }, {
                                                    onError: (err: any) => {
                                                        const msg = err.response?.data?.detail || err.message || 'Failed to cancel meeting';
                                                        alert(`Error: ${msg}`);
                                                    }
                                                });
                                            }
                                        }}
                                        disabled={updateMut.isPending}
                                    >
                                        Cancel
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
