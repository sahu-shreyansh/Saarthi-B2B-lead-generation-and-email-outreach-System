'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchSettings, createCheckout } from '@/lib/api';
import {
    User, Mail, Shield, CreditCard, Zap, Building2,
    ExternalLink, Check, Settings
} from 'lucide-react';

type SettingsTab = 'account' | 'plan' | 'upgrade' | 'workspace';

export default function SettingsPage() {
    const [tab, setTab] = useState<SettingsTab>('account');
    const [upgrading, setUpgrading] = useState('');

    const { data: settings, isLoading, error } = useQuery({
        queryKey: ['settings'],
        queryFn: fetchSettings,
    });

    // Also get user info from localStorage for editable fields
    const [localUser, setLocalUser] = useState({ full_name: '', email: '', company_name: '' });
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const stored = localStorage.getItem('saarthi_user');
            if (stored) {
                try { setLocalUser(JSON.parse(stored)); } catch { }
            }
        }
    }, []);

    // Merge API data with local
    const user = settings?.user || localUser;
    const subscription = settings?.subscription || { plan_type: 'free', monthly_limit: 100, subscription_status: 'active' };
    const accounts = settings?.sending_accounts || [];

    const handleUpgrade = async (plan: string) => {
        setUpgrading(plan);
        try {
            const data = await createCheckout(plan);
            if (data.checkout_url) {
                window.open(data.checkout_url, '_blank');
            } else {
                alert('Checkout URL not available. Make sure Stripe is configured in backend.');
            }
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to create checkout session. Check Stripe configuration.');
        } finally {
            setUpgrading('');
        }
    };

    const TABS: { key: SettingsTab; label: string; icon: any }[] = [
        { key: 'account', label: 'My Profile', icon: User },
        { key: 'workspace', label: 'Workspace', icon: Building2 },
        { key: 'plan', label: 'Plan & Usage', icon: CreditCard },
        { key: 'upgrade', label: 'Upgrade', icon: Zap },
    ];

    const PLANS = [
        {
            name: 'Free Starter', price: '$0', period: '/mo', plan_key: 'free',
            features: ['100 AI emails/month', '1 email account connection', 'Basic inbox tracking', 'Manual CSV import'],
            current: subscription.plan_type === 'free',
        },
        {
            name: 'Growth', price: '$49', period: '/mo', plan_key: 'starter',
            features: ['2,500 AI emails/month', 'Up to 5 email accounts', 'Advanced analytics & A/B testing', 'Priority email support', 'Automated warmup'],
            current: subscription.plan_type === 'starter', popular: true,
        },
        {
            name: 'Scale Pro', price: '$129', period: '/mo', plan_key: 'pro',
            features: ['10,000 AI emails/month', 'Unlimited email accounts', 'Deep personalization AI', 'API & Webhooks access', 'Dedicated success manager'],
            current: subscription.plan_type === 'pro',
        },
    ];

    return (
        <div className="page-container fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Settings & Billing</h1>
                    <p className="page-subtitle">Manage your personal profile, workspace preferences, and subscription.</p>
                </div>
            </div>

            {error && (
                <div style={{ padding: 16, marginBottom: 24, background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--danger)', borderRadius: 'var(--radius-sm)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Shield size={16} /> Failed to load settings. Make sure the backend database is running.
                </div>
            )}

            {/* Tabs */}
            <div className="tab-nav" style={{ marginBottom: 32 }}>
                {TABS.map(t => {
                    const Icon = t.icon;
                    return (
                        <button key={t.key} className={`tab-item ${tab === t.key ? 'active' : ''}`}
                            onClick={() => setTab(t.key)}>
                            <Icon size={14} /> {t.label}
                        </button>
                    );
                })}
            </div>

            {isLoading && <div className="card" style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}><Settings size={24} className="spin" style={{ margin: '0 auto 16px', opacity: 0.3 }} /><p>Loading your preferences...</p></div>}

            {/* ═══════ MY ACCOUNT ═══════ */}
            {tab === 'account' && !isLoading && (
                <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 24, alignItems: 'flex-start' }}>
                    <div className="card" style={{ padding: 32 }}>
                        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 24 }}>Personal Profile</h2>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 32, paddingBottom: 24, borderBottom: '1px solid var(--border-subtle)' }}>
                            <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: 24, fontWeight: 700 }}>
                                {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <button className="btn btn-secondary" style={{ marginBottom: 8 }}>Upload Avatar</button>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>JPG, GIF or PNG. 1MB max.</div>
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                            <div>
                                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Full Name</label>
                                <input value={user.full_name || ''} readOnly style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }} />
                            </div>
                            <div>
                                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Email Address</label>
                                <input value={user.email || ''} readOnly style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }} />
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Role / Job Title</label>
                                <input placeholder="e.g. Founder, Head of Sales" style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }} />
                            </div>
                            <div>
                                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Member Since</label>
                                <input value={user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'} readOnly
                                    style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', padding: '10px 14px', borderRadius: 'var(--radius-sm)' }} />
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 32, paddingTop: 24, borderTop: '1px solid var(--border-subtle)' }}>
                            <button className="btn btn-primary" disabled>Save Changes</button>
                        </div>
                    </div>

                    {/* Connected Accounts sidebar */}
                    <div className="card" style={{ padding: 24, background: 'var(--bg-surface)' }}>
                        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>
                            Connected Senders ({accounts.length})
                        </h3>
                        {accounts.length === 0 ? (
                            <div style={{ padding: 20, textAlign: 'center', border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)' }}>
                                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No accounts connected.</p>
                                <p style={{ fontSize: 12, color: 'var(--accent-primary)', marginTop: 8, cursor: 'pointer' }}>Go to Accounts →</p>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {accounts.map((acc: any) => (
                                    <div key={acc.id} style={{
                                        display: 'flex', alignItems: 'center', gap: 12, padding: '12px',
                                        background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)'
                                    }}>
                                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: acc.is_active ? 'var(--success)' : 'var(--danger)', boxShadow: acc.is_active ? '0 0 8px var(--success)' : 'none' }} />
                                        <span style={{ fontSize: 13, color: 'var(--text-primary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{acc.email}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ═══════ PLAN & USAGE ═══════ */}
            {tab === 'plan' && !isLoading && (
                <div className="fade-in" style={{ maxWidth: 800 }}>
                    <div className="card" style={{ padding: 32, marginBottom: 24 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
                            <div>
                                <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>Current Subscription</h2>
                                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>You are currently on the <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{subscription.plan_type}</strong> plan.</p>
                            </div>
                            <span className={`badge ${subscription.subscription_status === 'active' ? 'badge-green' : 'badge-red'}`} style={{ padding: '6px 12px', fontSize: 12 }}>
                                {subscription.subscription_status === 'active' ? 'Active' : 'Inactive'}
                            </span>
                        </div>

                        <div style={{ padding: 24, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Monthly Email Capacity</span>
                                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>10</strong> / {subscription.monthly_limit} sent</span>
                            </div>
                            <div style={{ height: 8, background: 'var(--bg-surface)', borderRadius: 4, overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: '5%', background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))' }} />
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
                                Resets on {subscription.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : 'the 1st of every month'}
                            </div>
                        </div>

                        {subscription.plan_type === 'free' && (
                            <div style={{ marginTop: 24, padding: 20, background: 'rgba(20, 184, 166, 0.05)', border: '1px solid rgba(20, 184, 166, 0.2)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent-primary)', marginBottom: 4 }}>Unlock higher limits</div>
                                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Upgrade to a paid plan to send up to 10,000 personalized emails per month.</div>
                                </div>
                                <button className="btn btn-primary" onClick={() => setTab('upgrade')} style={{ boxShadow: '0 0 15px var(--accent-glow)' }}>
                                    <Zap size={14} /> View Plans
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ═══════ UPGRADE ═══════ */}
            {tab === 'upgrade' && (
                <div className="fade-in">
                    <div style={{ textAlign: 'center', marginBottom: 40, marginTop: 20 }}>
                        <h2 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>Simple, transparent pricing</h2>
                        <p style={{ fontSize: 15, color: 'var(--text-secondary)', maxWidth: 500, margin: '0 auto' }}>Scale your outbound pipeline with AI. No hidden fees or surprise charges.</p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24, maxWidth: 1100, margin: '0 auto' }}>
                        {PLANS.map((plan, i) => (
                            <div key={plan.name} className="card" style={{
                                padding: 32, position: 'relative', display: 'flex', flexDirection: 'column',
                                border: plan.popular ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                background: plan.popular ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                                transform: plan.popular ? 'scale(1.02)' : 'scale(1)',
                                boxShadow: plan.popular ? '0 0 30px rgba(20, 184, 166, 0.05)' : 'none',
                                zIndex: plan.popular ? 2 : 1,
                            }}>
                                {plan.popular && (
                                    <div style={{
                                        position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                                        padding: '4px 16px', borderRadius: 20, fontSize: 11, fontWeight: 800,
                                        background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', color: '#000',
                                        boxShadow: '0 0 15px var(--accent-glow)', letterSpacing: '0.05em'
                                    }}>
                                        MOST POPULAR
                                    </div>
                                )}
                                <h3 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>{plan.name}</h3>
                                <div style={{ marginBottom: 32, display: 'flex', alignItems: 'baseline', gap: 4 }}>
                                    <span style={{ fontSize: 40, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.04em' }}>{plan.price}</span>
                                    <span style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 500 }}>{plan.period}</span>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, flex: 1, marginBottom: 32 }}>
                                    {plan.features.map(f => (
                                        <div key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                            <Check size={16} color="var(--accent-primary)" style={{ marginTop: 2, flexShrink: 0 }} /> {f}
                                        </div>
                                    ))}
                                </div>
                                {plan.current ? (
                                    <button className="btn btn-secondary" disabled style={{ width: '100%', padding: '12px', opacity: 0.5 }}>Current Plan</button>
                                ) : plan.plan_key === 'free' ? (
                                    <button className="btn btn-secondary" disabled style={{ width: '100%', padding: '12px', opacity: 0.5 }}>Included in Free</button>
                                ) : (
                                    <button className="btn btn-primary" style={{ width: '100%', padding: '12px', background: plan.popular ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))' : 'var(--bg-elevated)', border: plan.popular ? 'none' : '1px solid var(--accent-primary)', color: plan.popular ? '#000' : 'var(--accent-primary)' }}
                                        onClick={() => handleUpgrade(plan.plan_key)}
                                        disabled={!!upgrading}>
                                        {upgrading === plan.plan_key ? 'Redirecting to Stripe...' : `Upgrade to ${plan.name}`}
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ═══════ WORKSPACE ═══════ */}
            {tab === 'workspace' && !isLoading && (
                <div className="card fade-in" style={{ padding: 32, maxWidth: 640 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 24 }}>Workspace Settings</h2>

                    <div style={{ marginBottom: 24 }}>
                        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Organization Name</label>
                        <input value={user.company_name || 'My Organization'} readOnly style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', padding: '12px 14px', borderRadius: 'var(--radius-sm)' }} />
                    </div>

                    <div style={{ marginBottom: 32 }}>
                        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 8, fontWeight: 600 }}>Default Timezone</label>
                        <select defaultValue="Asia/Kolkata" style={{ width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)', padding: '12px 14px', borderRadius: 'var(--radius-sm)' }}>
                            <option value="Asia/Kolkata">(GMT+05:30) India Standard Time</option>
                            <option value="America/New_York">(GMT-05:00) Eastern Time</option>
                            <option value="America/Los_Angeles">(GMT-08:00) Pacific Time</option>
                            <option value="Europe/London">(GMT+00:00) London</option>
                        </select>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>This timezone will be used as the default for all new campaign schedules.</p>
                    </div>

                    <div style={{ paddingTop: 24, borderTop: '1px solid var(--border-subtle)' }}>
                        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 12, fontWeight: 600 }}>Workspace Owner</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                            <div style={{
                                width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: '#000', fontSize: 16, fontWeight: 700,
                            }}>
                                {(user.full_name || user.email || 'U').charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{user.full_name || 'User'}</div>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{user.email}</div>
                            </div>
                            <div className="badge badge-gray" style={{ marginLeft: 'auto', background: 'var(--bg-surface)' }}>Owner</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
