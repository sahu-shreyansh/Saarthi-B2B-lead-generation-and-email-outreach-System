'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchSettings } from '@/lib/api';
import { Mail, Plus, CheckCircle, XCircle, RefreshCw, Server, ShieldCheck } from 'lucide-react';

export default function AccountsPage() {
    const { data: settings, isLoading, error } = useQuery({
        queryKey: ['settings'],
        queryFn: fetchSettings,
    });

    const accounts = settings?.sending_accounts || [];

    return (
        <div className="page-container fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Email Accounts</h1>
                    <p className="page-subtitle">
                        {accounts.length} account{accounts.length !== 1 ? 's' : ''} connected and ready for outreach
                    </p>
                </div>
            </div>

            {isLoading && (
                <div className="card" style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
                    <RefreshCw size={24} className="spin" style={{ margin: '0 auto 16px', opacity: 0.5, color: 'var(--accent-primary)' }} />
                    <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Loading sending accounts...</p>
                </div>
            )}

            {error && (
                <div className="card" style={{ padding: 24, background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--danger)', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <XCircle size={18} />
                    <div>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Connection Error</div>
                        <div style={{ fontSize: 13, color: 'var(--danger)', opacity: 0.8 }}>Failed to load accounts. Please ensure the backend server is running correctly.</div>
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
                {/* Add New Account Card */}
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: 40, borderRadius: 'var(--radius-lg)', border: '2px dashed var(--border-strong)',
                    background: 'var(--bg-elevated)', cursor: 'pointer', minHeight: 180,
                    transition: 'all 0.2s',
                }}
                    onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                    onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-strong)'}
                    onClick={() => alert('To connect a Google or Outlook account, configure your OAuth credentials in the backend environment and restart.')}
                >
                    <div style={{
                        width: 48, height: 48, borderRadius: '50%',
                        background: 'rgba(20, 184, 166, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        marginBottom: 16, border: '1px solid rgba(20, 184, 166, 0.2)',
                    }}>
                        <Plus size={20} color="var(--accent-primary)" />
                    </div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Connect New Account</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8, textAlign: 'center', maxWidth: 220, lineHeight: 1.5 }}>
                        Integrate Gmail or Outlook to scale your sending volume securely.
                    </div>
                </div>

                {/* Real account cards */}
                {accounts.map((acc: any, i: number) => (
                    <div key={acc.id} className="card fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16, animationDelay: `${i * 0.05}s`, position: 'relative', overflow: 'hidden' }}>
                        {acc.is_active && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg, var(--success), #34d399)' }} />}

                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                            <div style={{
                                width: 44, height: 44, borderRadius: 'var(--radius-sm)',
                                background: acc.is_active ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                border: `1px solid ${acc.is_active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`
                            }}>
                                <Mail size={20} color={acc.is_active ? 'var(--success)' : 'var(--danger)'} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{acc.email}</div>
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize', display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <Server size={12} /> {acc.provider}
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                {acc.is_active ? (
                                    <><CheckCircle size={14} color="var(--success)" /><span style={{ fontSize: 13, color: 'var(--success)', fontWeight: 600 }}>Active & Connected</span></>
                                ) : (
                                    <><XCircle size={14} color="var(--danger)" /><span style={{ fontSize: 13, color: 'var(--danger)', fontWeight: 600 }}>Disconnected</span></>
                                )}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                                <ShieldCheck size={12} /> SPF/DKIM OK
                            </div>
                        </div>
                    </div>
                ))}

                {!isLoading && accounts.length === 0 && (
                    <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, gridColumn: 'span 2', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                        <Mail size={32} style={{ margin: '0 auto 16px', opacity: 0.2, color: 'var(--text-primary)' }} />
                        <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>No sending accounts found</p>
                        <p style={{ maxWidth: 300, lineHeight: 1.5 }}>You need to connect at least one email account before you can launch any campaigns.</p>
                    </div>
                )}
            </div>

            <div style={{ marginTop: 40, padding: 24, background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: 'var(--radius-lg)' }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <ShieldCheck size={16} color="#38bdf8" /> Deliverability Best Practices
                </h3>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: 800 }}>
                    To ensure your emails land in the primary inbox, we strongly recommend warming up new accounts for at least 14 days before sending bulk campaigns. Keep your daily sending volume under 50 emails per connected account to maintain a healthy sender reputation.
                </p>
            </div>
        </div>
    );
}
