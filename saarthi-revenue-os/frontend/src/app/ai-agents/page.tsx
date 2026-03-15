'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    BrainCircuit, Zap, MessageSquare, ChevronDown, ChevronRight,
    Loader2, CheckCircle, AlertCircle, History, Send
} from 'lucide-react';
import { generateEmailSync, classifyReply, fetchAiOutputs } from '@/lib/api';

// ─── Status Badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
    const colorMap: Record<string, string> = {
        success: 'badge-success',
        failed: 'badge-danger',
        fallback: 'badge-warning',
    };
    return <span className={`badge ${colorMap[status] ?? 'badge-gray'}`}>{status}</span>;
}

// ─── 1. Email Generation Panel ────────────────────────────────────────────────

function EmailGeneratorPanel() {
    const [leadId, setLeadId] = useState('');
    const [mode, setMode] = useState<'normal' | 'classifier'>('normal');
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const mutation = useMutation({
        mutationFn: () => generateEmailSync({
            lead_id: leadId,
            mode,
            services: [],
        }),
        onSuccess: (data) => {
            setResult(data);
            setError(null);
        },
        onError: (err: any) => {
            setError(err.response?.data?.detail || 'Email generation failed');
            setResult(null);
        },
    });

    return (
        <div className="card-flat">
            <div className="flex items-center gap-3 mb-6">
                <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                    <Zap size={18} color="var(--accent-primary)" />
                </div>
                <div>
                    <div className="section-title">Generate Cold Email</div>
                    <div className="text-meta">AI-powered personalized outreach from lead profile</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <div className="form-group">
                    <label className="form-label">Lead ID</label>
                    <input
                        id="ai-lead-id"
                        className="input"
                        placeholder="Paste lead UUID…"
                        value={leadId}
                        onChange={e => setLeadId(e.target.value)}
                    />
                </div>
                <div className="form-group">
                    <label className="form-label">Mode</label>
                    <select
                        id="ai-mode-select"
                        className="input"
                        value={mode}
                        onChange={e => setMode(e.target.value as 'normal' | 'classifier')}
                    >
                        <option value="normal">Normal (paragraph services)</option>
                        <option value="classifier">Classifier (scored services)</option>
                    </select>
                </div>
            </div>

            <button
                id="ai-generate-email-btn"
                className="btn btn-primary"
                onClick={() => mutation.mutate()}
                disabled={!leadId || mutation.isPending}
            >
                {mutation.isPending
                    ? <><Loader2 size={14} className="animate-spin" /> Generating…</>
                    : <><Send size={14} /> Generate Email</>}
            </button>

            {error && (
                <div className="flex items-center gap-2 mt-4" style={{
                    padding: '10px 14px', background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8,
                    color: 'var(--danger)', fontSize: 13
                }}>
                    <AlertCircle size={14} />
                    <span>{error}</span>
                </div>
            )}

            {result && (
                <div style={{ marginTop: 20 }}>
                    {/* Email Output */}
                    <div style={{
                        padding: 16, background: 'var(--bg-hover)',
                        borderRadius: 8, border: '1px solid var(--border)', marginBottom: 12
                    }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Generated Email</div>
                        <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                            {result.email?.subject || '—'}
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                            {result.email?.body || '—'}
                        </div>
                    </div>

                    {/* Signal Report */}
                    {result.signal_report && (
                        <div style={{
                            padding: 16, background: 'var(--bg-hover)',
                            borderRadius: 8, border: '1px solid var(--border)', marginBottom: 12
                        }}>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>Signal Report</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                {Object.entries(result.signal_report as Record<string, string>).map(([k, v]) => (
                                    <div key={k}>
                                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2, textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</div>
                                        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{v}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Why This Works */}
                    {result.why_this_works && (
                        <div style={{ padding: 16, background: 'rgba(16,185,129,0.06)', borderRadius: 8, border: '1px solid rgba(16,185,129,0.15)' }}>
                            <div style={{ fontSize: 11, color: 'var(--success)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Why This Works</div>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                {result.why_this_works.why_wont_feel_generic || '—'}
                                {result.why_this_works.word_count && (
                                    <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
                                        · {result.why_this_works.word_count} words
                                        · Depth: {result.why_this_works.personalization_depth}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── 2. Reply Classifier Panel ────────────────────────────────────────────────

const INTENT_COLORS: Record<string, string> = {
    interested: 'badge-success',
    meeting_request: 'badge-cyan',
    not_interested: 'badge-danger',
    out_of_office: 'badge-warning',
    bounce: 'badge-danger',
    unclear: 'badge-gray',
};

function ReplyClassifierPanel() {
    const [replyId, setReplyId] = useState('');
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const mutation = useMutation({
        mutationFn: () => classifyReply(replyId),
        onSuccess: (data) => { setResult(data); setError(null); },
        onError: (err: any) => {
            setError(err.response?.data?.detail || 'Classification failed');
            setResult(null);
        },
    });

    return (
        <div className="card-flat">
            <div className="flex items-center gap-3 mb-6">
                <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: 'rgba(6,182,212,0.12)', border: '1px solid rgba(6,182,212,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <MessageSquare size={18} color="var(--accent-cyan)" />
                </div>
                <div>
                    <div className="section-title">Classify Reply</div>
                    <div className="text-meta">Detect intent from an incoming email reply</div>
                </div>
            </div>

            <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Reply ID</label>
                <input
                    id="reply-id-input"
                    className="input"
                    placeholder="Paste email reply UUID…"
                    value={replyId}
                    onChange={e => setReplyId(e.target.value)}
                />
            </div>

            <button
                id="classify-reply-btn"
                className="btn btn-secondary"
                onClick={() => mutation.mutate()}
                disabled={!replyId || mutation.isPending}
            >
                {mutation.isPending
                    ? <><Loader2 size={14} className="animate-spin" /> Classifying…</>
                    : <><BrainCircuit size={14} /> Classify Intent</>}
            </button>

            {error && (
                <div className="flex items-center gap-2 mt-4" style={{
                    padding: '10px 14px', background: 'rgba(239,68,68,0.08)',
                    border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8,
                    color: 'var(--danger)', fontSize: 13
                }}>
                    <AlertCircle size={14} />
                    <span>{error}</span>
                </div>
            )}

            {result && (
                <div style={{ marginTop: 20, display: 'grid', gap: 12 }}>
                    <div style={{
                        padding: 16, background: 'var(--bg-hover)',
                        borderRadius: 8, border: '1px solid var(--border)'
                    }}>
                        <div className="flex items-center gap-3 mb-3">
                            <CheckCircle size={16} color="var(--success)" />
                            <span style={{ fontWeight: 600, fontSize: 14 }}>Classification Result</span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                            <div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Intent</div>
                                <span className={`badge ${INTENT_COLORS[result.intent] ?? 'badge-gray'}`}>
                                    {result.intent}
                                </span>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Confidence</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{result.confidence}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Recommended Action</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{result.recommended_action}</div>
                            </div>
                        </div>
                        {result.key_signal && (
                            <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--bg-card)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)' }}>
                                <span style={{ color: 'var(--text-muted)', marginRight: 6 }}>Key signal:</span>
                                {result.key_signal}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── 3. AI Output History ─────────────────────────────────────────────────────

function ExpandedRow({ row }: { row: any }) {
    const json = row.response_json;
    return (
        <div style={{ padding: 16, background: 'var(--bg-card)', borderRadius: 8, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace', whiteSpace: 'pre-wrap', overflowX: 'auto', maxHeight: 400, overflow: 'auto' }}>
            {JSON.stringify(json, null, 2)}
        </div>
    );
}

function OutputHistoryPanel() {
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const { data: outputs = [], isLoading } = useQuery({
        queryKey: ['ai-outputs'],
        queryFn: () => fetchAiOutputs(undefined, 30),
        refetchInterval: 30000,
    });

    const AGENT_COLOR: Record<string, string> = {
        email_pipeline: 'badge-blue',
        signal: 'badge-cyan',
        classifier: 'badge-warning',
        reply_classifier: 'badge-success',
    };

    return (
        <div className="card-flat">
            <div className="flex items-center gap-3 mb-6">
                <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <History size={18} color="var(--warning)" />
                </div>
                <div>
                    <div className="section-title">AI Output History</div>
                    <div className="text-meta">All recent agent runs for this organization</div>
                </div>
            </div>

            <div className="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style={{ width: 28 }} />
                            <th>Agent</th>
                            <th>Lead ID</th>
                            <th>Model</th>
                            <th>Tokens</th>
                            <th>Status</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading
                            ? [1, 2, 3, 4].map(i => (
                                <tr key={i}>
                                    {[1, 2, 3, 4, 5, 6, 7].map(j => (
                                        <td key={j}><div className="skeleton" style={{ height: 12, borderRadius: 4 }} /></td>
                                    ))}
                                </tr>
                            ))
                            : (outputs as any[]).length === 0
                                ? (
                                    <tr>
                                        <td colSpan={7}>
                                            <div className="empty-state">
                                                <BrainCircuit size={32} color="var(--text-muted)" />
                                                <p className="empty-state-text">No AI runs yet.</p>
                                                <p className="text-meta">Generate an email above to see results here.</p>
                                            </div>
                                        </td>
                                    </tr>
                                )
                                : (outputs as any[]).map((row: any) => (
                                    <>
                                        <tr
                                            key={row.id}
                                            style={{ cursor: 'pointer' }}
                                            onClick={() => setExpandedId(expandedId === row.id ? null : row.id)}
                                        >
                                            <td>
                                                {expandedId === row.id
                                                    ? <ChevronDown size={14} color="var(--text-muted)" />
                                                    : <ChevronRight size={14} color="var(--text-muted)" />}
                                            </td>
                                            <td>
                                                <span className={`badge ${AGENT_COLOR[row.agent_type] ?? 'badge-gray'}`}>
                                                    {row.agent_type}
                                                </span>
                                            </td>
                                            <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>
                                                {row.lead_id ? row.lead_id.slice(0, 8) + '…' : '—'}
                                            </td>
                                            <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                                {row.model_used ? row.model_used.split('/').pop() : '—'}
                                            </td>
                                            <td style={{ fontSize: 12 }}>{row.tokens_used?.toLocaleString() ?? '—'}</td>
                                            <td><StatusBadge status={row.status} /></td>
                                            <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                                {new Date(row.created_at).toLocaleString()}
                                            </td>
                                        </tr>
                                        {expandedId === row.id && (
                                            <tr key={`${row.id}-expanded`}>
                                                <td colSpan={7} style={{ padding: '0 16px 16px' }}>
                                                    <ExpandedRow row={row} />
                                                </td>
                                            </tr>
                                        )}
                                    </>
                                ))
                        }
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AIAgentsPage() {
    const [activeTab, setActiveTab] = useState<'email' | 'reply' | 'history'>('email');

    const TABS = [
        { key: 'email', label: 'Email Generator', icon: Zap },
        { key: 'reply', label: 'Reply Classifier', icon: MessageSquare },
        { key: 'history', label: 'Output History', icon: History },
    ] as const;

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <div className="page-header-left">
                    <h1>AI Agents</h1>
                    <p>Control the AI pipeline — generate emails, classify replies, view agent runs</p>
                </div>
            </div>

            {/* Tab Bar */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 0 }}>
                {TABS.map(({ key, label, icon: Icon }) => (
                    <button
                        key={key}
                        id={`ai-tab-${key}`}
                        onClick={() => setActiveTab(key)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '10px 18px', fontSize: 13, fontWeight: 500,
                            background: 'none', border: 'none', cursor: 'pointer',
                            borderBottom: activeTab === key ? '2px solid var(--accent-primary)' : '2px solid transparent',
                            color: activeTab === key ? 'var(--accent-primary)' : 'var(--text-muted)',
                            transition: 'color 0.15s',
                            marginBottom: -1,
                        }}
                    >
                        <Icon size={14} />
                        {label}
                    </button>
                ))}
            </div>

            {/* Tab Panels */}
            {activeTab === 'email' && <EmailGeneratorPanel />}
            {activeTab === 'reply' && <ReplyClassifierPanel />}
            {activeTab === 'history' && <OutputHistoryPanel />}
        </div>
    );
}
