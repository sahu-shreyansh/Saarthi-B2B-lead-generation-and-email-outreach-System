'use client';

import { useState } from 'react';
import { useInboxThreads, useInboxMessages, useReplyToThread } from '@/hooks/useInbox';
import {
    Inbox as InboxIcon, Send, MessageSquare, Search, User
} from 'lucide-react';

const FILTERS = [
    { value: '', label: 'All' },
    { value: 'active', label: 'Active' },
    { value: 'closed', label: 'Closed' },
];

export default function InboxPage() {
    const [filter, setFilter] = useState('');
    const [activeId, setActiveId] = useState<string | null>(null);
    const [replyText, setReplyText] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const { data: threads = [], isLoading } = useInboxThreads(filter || undefined);

    const { data: messages = [], isLoading: messagesLoading } = useInboxMessages(activeId || '');

    const replyMut = useReplyToThread();

    const filteredThreads = (threads as any[]).filter((thread: any) => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return thread.subject?.toLowerCase().includes(q);
    });

    const statusBadge = (status: string) => {
        if (status === 'active') return 'badge-success';
        if (status === 'closed') return 'badge-gray';
        return 'badge-blue';
    };

    return (
        <div className="flex h-full w-full bg-base overflow-hidden">
            {/* Left: Thread list */}
            <div className="flex-col h-full bg-surface border-r border-border shrink-0 z-10" style={{ width: 340 }}>

                {/* Header */}
                <div className="p-4 border-b border-border">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="flex items-center justify-center rounded shrink-0 bg-primary/10 text-primary" style={{ width: 32, height: 32 }}>
                            <InboxIcon size={16} />
                        </div>
                        <h2 className="text-xl font-bold m-0 leading-none text-primary-text">Inbox</h2>
                    </div>

                    {/* Search */}
                    <div className="relative mb-3">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" style={{ pointerEvents: 'none' }} />
                        <input
                            className="input w-full bg-base"
                            style={{ paddingLeft: 34 }}
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            placeholder="Search subjects..."
                        />
                    </div>

                    {/* Filters */}
                    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 hide-scrollbar">
                        {FILTERS.map(f => {
                            const active = filter === f.value;
                            return (
                                <button
                                    key={f.value}
                                    onClick={() => setFilter(f.value)}
                                    className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors border ${active ? 'border-focus text-primary bg-focus/10' : 'border-border text-secondary hover:border-focus bg-transparent'
                                        }`}
                                >
                                    {f.label}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Thread List */}
                <div className="flex-1 overflow-auto">
                    {isLoading ? (
                        <div className="p-8 text-center text-muted">Loading threads...</div>
                    ) : filteredThreads.length === 0 ? (
                        <div className="p-8 text-center text-muted flex-col items-center">
                            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-hover mb-4 mx-auto">
                                <InboxIcon size={20} className="text-secondary" />
                            </div>
                            <p className="font-semibold text-primary mb-1">No conversations found</p>
                            <p className="text-sm">Replies will appear here once campaigns begin.</p>
                        </div>
                    ) : (
                        filteredThreads.map((thread: any) => {
                            const badgeCls = statusBadge(thread.status);
                            const isActive = activeId === thread.id;
                            return (
                                <div
                                    key={thread.id}
                                    onClick={() => setActiveId(thread.id)}
                                    className={`p-4 cursor-pointer border-b border-border transition-colors border-l-4 ${isActive ? 'bg-hover border-l-focus' : 'bg-transparent border-l-transparent hover:bg-hover/50'
                                        }`}
                                >
                                    <div className="flex justify-between items-center mb-1">
                                        <span className={`text-sm font-semibold truncate pr-2 ${isActive ? 'text-primary' : 'text-primary-text'}`}>
                                            {thread.subject || 'No Subject'}
                                        </span>
                                        <span className={`badge ${badgeCls}`} style={{ fontSize: 10, padding: '2px 6px' }}>
                                            {thread.status || 'unknown'}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted truncate w-full">
                                        Last active: {new Date(thread.latest_message_at).toLocaleString()}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Right: Messages view */}
            <div className="flex-1 flex-col h-full bg-base">
                {!activeId ? (
                    <div className="flex-1 flex items-center justify-center text-muted p-8">
                        <div className="text-center max-w-sm">
                            <div className="flex items-center justify-center w-16 h-16 rounded-full bg-surface border-2 border-dashed border-border mx-auto mb-4">
                                <MessageSquare size={24} className="text-secondary" />
                            </div>
                            <h3 className="text-lg font-semibold text-primary mb-2">Select a thread</h3>
                            <p className="text-sm">Choose a thread from the panel to read and reply.</p>
                        </div>
                    </div>
                ) : messagesLoading ? (
                    <div className="flex-1 flex items-center justify-center text-muted">
                        Loading messages...
                    </div>
                ) : (
                    <div className="flex-1 flex flex-col h-full fade-in">
                        {/* Messages Area */}
                        <div className="flex-1 overflow-auto p-4 md:p-6 lg:px-8 flex flex-col gap-6">
                            {(messages as any[]).map((msg: any) => {
                                const isUser = msg.direction === 'outgoing';
                                return (
                                    <div key={msg.id} className="fade-in max-w-3xl w-full" style={{ alignSelf: isUser ? 'flex-end' : 'flex-start' }}>
                                        <div className={`p-4 rounded-lg ${isUser ? 'bg-focus/10 border border-focus/20 ml-auto' : 'bg-card border border-border mr-auto'}`} style={{ width: 'fit-content', minWidth: 200, maxWidth: '100%' }}>
                                            {msg.subject && (
                                                <div className={`text-sm font-bold text-primary pb-3 mb-3 border-b ${isUser ? 'border-focus/20' : 'border-border'}`}>
                                                    {msg.subject}
                                                </div>
                                            )}
                                            <div className="text-sm text-primary leading-relaxed whitespace-pre-wrap">
                                                {msg.body}
                                            </div>
                                            {msg.ai_response && !isUser && (
                                                <div className="mt-3 p-3 bg-surface border border-border rounded-md text-xs">
                                                    <strong>AI Draft:</strong> {msg.ai_response}
                                                </div>
                                            )}
                                            <div className="text-xs text-muted mt-3 font-medium text-right flex justify-between">
                                                <span>Intent: {msg.intent}</span>
                                                <span>{isUser ? 'You' : msg.sender_name || msg.sender_email} &middot; {new Date(msg.received_at).toLocaleString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Reply box */}
                        <div className="p-4 md:px-6 border-t border-border bg-surface shrink-0 flex items-end gap-3 mt-auto">
                            <textarea
                                value={replyText}
                                onChange={e => setReplyText(e.target.value)}
                                placeholder="Type your reply to continue the conversation..."
                                rows={3}
                                className="input flex-1 py-3"
                                style={{ resize: 'none' }}
                            />
                            <button
                                onClick={() => {
                                    if (!replyText.trim()) return;
                                    replyMut.mutate(activeId, {
                                        onSuccess: () => {
                                            setReplyText('');
                                            // Optional: refetch messages
                                        },
                                        onError: (err: any) => {
                                            const msg = err.response?.data?.detail || err.message || 'Failed to send reply';
                                            alert(`Error: ${msg}`);
                                        }
                                    });
                                }}
                                disabled={!replyText.trim() || replyMut.isPending}
                                className="btn btn-primary cursor-pointer shrink-0"
                                style={{ height: 48, padding: '0 24px' }}
                            >
                                <Send size={16} /> {replyMut.isPending ? 'Sending...' : 'Send'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <style jsx global>{`
                .hide-scrollbar::-webkit-scrollbar { display: none; }
                .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
                .text-primary-text { color: var(--text-primary); }
            `}</style>
        </div>
    );
}
