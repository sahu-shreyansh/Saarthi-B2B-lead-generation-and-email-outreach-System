'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { fetchConversations, fetchConversation, sendReply } from '@/lib/api';
import {
    Inbox as InboxIcon, Send, MessageSquare, ArrowLeft, Search, User
} from 'lucide-react';

const FILTERS = [
    { value: '', label: 'All' },
    { value: 'replied', label: 'Replied' },
    { value: 'no_reply', label: 'No Reply' },
    { value: 'positive', label: 'Positive' },
    { value: 'negative', label: 'Negative' },
    { value: 'ooo', label: 'OOO' },
];

export default function InboxPage() {
    const [filter, setFilter] = useState('');
    const [activeId, setActiveId] = useState<string | null>(null);
    const [replyText, setReplyText] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const { data: conversations = [], isLoading, refetch: refetchList } = useQuery({
        queryKey: ['conversations', filter],
        queryFn: () => fetchConversations(filter || undefined),
    });

    const { data: activeConv, isLoading: convLoading } = useQuery({
        queryKey: ['conversation', activeId],
        queryFn: () => fetchConversation(activeId!),
        enabled: !!activeId,
    });

    const replyMut = useMutation({
        mutationFn: () => sendReply(activeId!, replyText),
        onSuccess: () => {
            setReplyText('');
            refetchList();
        },
        onError: (err: any) => alert(err?.response?.data?.detail || 'Reply failed'),
    });

    const filteredConversations = conversations.filter((conv: any) => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return conv.lead_name?.toLowerCase().includes(q) ||
            conv.lead_email?.toLowerCase().includes(q) ||
            conv.lead_company?.toLowerCase().includes(q);
    });

    const statusColor = (status: string, type: string) => {
        if (type === 'POSITIVE') return 'var(--success)';
        if (type === 'NEGATIVE') return 'var(--danger)';
        if (type === 'OOO') return 'var(--warning)';
        if (status === 'REPLIED') return 'var(--accent-primary)';
        return 'var(--text-secondary)';
    };

    return (
        <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
            {/* Left: Conversation list */}
            <div style={{
                width: 380, minWidth: 380, background: 'var(--bg-surface)',
                borderRight: '1px solid var(--border-subtle)',
                display: 'flex', flexDirection: 'column',
                zIndex: 5,
            }}>
                {/* Header */}
                <div style={{ padding: '24px 24px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <InboxIcon size={16} color="#fff" />
                        </div>
                        <h2 className="page-title" style={{ fontSize: 20, marginBottom: 0 }}>Inbox</h2>
                    </div>

                    {/* Search */}
                    <div style={{ position: 'relative', marginBottom: 16 }}>
                        <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                        <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                            placeholder="Search by name or email..."
                            style={{ width: '100%', paddingLeft: 36, background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} />
                    </div>

                    {/* Filters */}
                    <div className="filter-scroll" style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4, margin: '0 -4px', paddingLeft: 4 }}>
                        {FILTERS.map(f => (
                            <button
                                key={f.value}
                                onClick={() => setFilter(f.value)}
                                style={{
                                    padding: '6px 12px', borderRadius: 'var(--radius-full)', fontSize: 12, cursor: 'pointer',
                                    border: filter === f.value ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                    background: filter === f.value ? 'rgba(20, 184, 166, 0.1)' : 'transparent',
                                    color: filter === f.value ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                    fontWeight: filter === f.value ? 600 : 500,
                                    whiteSpace: 'nowrap', transition: 'all 0.2s',
                                }}
                            >
                                {f.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Conversation List */}
                <div style={{ flex: 1, overflow: 'auto' }}>
                    {isLoading ? (
                        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading threads...</div>
                    ) : filteredConversations.length === 0 ? (
                        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                            <InboxIcon size={32} style={{ margin: '0 auto 16px', opacity: 0.2, color: 'var(--accent-primary)' }} />
                            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>No conversations found</p>
                            <p style={{ fontSize: 12, marginTop: 8 }}>Replies will appear here once campaigns are active.</p>
                        </div>
                    ) : (
                        filteredConversations.map((conv: any, i: number) => {
                            const badgeColor = statusColor(conv.reply_status, conv.reply_type);
                            return (
                                <div
                                    key={conv.id}
                                    onClick={() => setActiveId(conv.id)}
                                    className="fade-in"
                                    style={{
                                        padding: '16px 24px', cursor: 'pointer',
                                        borderBottom: '1px solid var(--border-subtle)',
                                        background: activeId === conv.id ? 'var(--bg-hover)' : 'transparent',
                                        borderLeft: activeId === conv.id ? '3px solid var(--accent-primary)' : '3px solid transparent',
                                        transition: 'all 0.15s',
                                        animationDelay: `${i * 0.03}s`
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{conv.lead_name}</span>
                                        <span style={{
                                            padding: '2px 8px', borderRadius: 'var(--radius-sm)', fontSize: 10, fontWeight: 700,
                                            color: badgeColor, border: `1px solid ${badgeColor}30`, background: `${badgeColor}10`,
                                        }}>
                                            {conv.reply_type || conv.reply_status}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
                                        {conv.lead_company} · {conv.lead_email}
                                    </div>
                                    <div style={{
                                        fontSize: 12, color: 'var(--text-muted)',
                                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const,
                                        width: '100%',
                                    }}>
                                        {conv.last_snippet || '(No messages)'}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Right: Thread view */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
                {!activeId ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                        <div style={{ textAlign: 'center', maxWidth: 300 }}>
                            <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'var(--bg-surface)', border: '1px dashed var(--border-strong)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
                                <MessageSquare size={24} color="var(--accent-primary)" style={{ opacity: 0.5 }} />
                            </div>
                            <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>Select a conversation</h3>
                            <p style={{ fontSize: 13, lineHeight: 1.5 }}>Choose a thread from the panel to read and reply to your prospects.</p>
                        </div>
                    </div>
                ) : convLoading ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                        Loading thread...
                    </div>
                ) : activeConv ? (
                    <div className="fade-in" style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
                        {/* Thread Header */}
                        <div style={{
                            padding: '24px 32px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-surface)',
                            display: 'flex', alignItems: 'center', gap: 16, zIndex: 2
                        }}>
                            <div style={{
                                width: 44, height: 44, borderRadius: '50%',
                                background: 'rgba(20, 184, 166, 0.1)', border: '1px solid rgba(20, 184, 166, 0.2)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'var(--accent-primary)', fontSize: 16, fontWeight: 700,
                            }}>
                                {activeConv.lead?.name?.[0]?.toUpperCase() || <User size={20} />}
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{activeConv.lead?.name}</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{activeConv.lead?.email} · {activeConv.lead?.company}</div>
                            </div>
                        </div>

                        {/* Messages */}
                        <div style={{ flex: 1, overflow: 'auto', padding: '32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
                            {(activeConv.messages || []).map((msg: any) => (
                                <div key={msg.id} className="fade-in" style={{
                                    padding: '20px 24px', borderRadius: 'var(--radius-md)', maxWidth: '85%',
                                    alignSelf: msg.sender_type === 'USER' ? 'flex-end' : 'flex-start',
                                    background: msg.sender_type === 'USER' ? 'rgba(20, 184, 166, 0.1)' : 'var(--bg-elevated)',
                                    border: `1px solid ${msg.sender_type === 'USER' ? 'rgba(20, 184, 166, 0.2)' : 'var(--border-subtle)'}`,
                                    boxShadow: msg.sender_type === 'USER' ? '0 0 20px rgba(20, 184, 166, 0.05)' : 'none',
                                }}>
                                    {msg.subject && (
                                        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12, paddingBottom: 12, borderBottom: `1px solid ${msg.sender_type === 'USER' ? 'rgba(20, 184, 166, 0.2)' : 'var(--border-subtle)'}` }}>
                                            {msg.subject}
                                        </div>
                                    )}
                                    <div style={{ fontSize: 14, color: 'var(--text-primary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{msg.body}</div>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, textAlign: 'right', fontWeight: 500 }}>
                                        {msg.sender_type === 'USER' ? 'You' : activeConv.lead?.name} · {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Reply box */}
                        <div style={{
                            padding: '20px 32px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-surface)',
                            display: 'flex', gap: 16, alignItems: 'flex-end',
                        }}>
                            <textarea
                                value={replyText}
                                onChange={e => setReplyText(e.target.value)}
                                placeholder="Type your reply to continue the conversation..."
                                rows={3}
                                style={{
                                    flex: 1, resize: 'none', background: 'var(--bg-base)',
                                    border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-md)',
                                    padding: '16px', fontSize: 14, color: 'var(--text-primary)',
                                    boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.2)'
                                }}
                            />
                            <button
                                onClick={() => replyText.trim() && replyMut.mutate()}
                                disabled={!replyText.trim() || replyMut.isPending}
                                className="btn btn-primary"
                                style={{ padding: '12px 24px', height: 48, boxShadow: '0 0 15px var(--accent-glow)' }}
                            >
                                <Send size={16} /> {replyMut.isPending ? 'Sending...' : 'Send Reply'}
                            </button>
                        </div>
                    </div>
                ) : null}
            </div>
            <style>{`.filter-scroll::-webkit-scrollbar { display: none; }`}</style>
        </div>
    );
}
