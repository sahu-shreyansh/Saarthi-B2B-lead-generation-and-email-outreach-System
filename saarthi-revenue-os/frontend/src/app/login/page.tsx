'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login, register } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { Zap, Mail, Lock, Building2 } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [orgName, setOrgName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            let data: any;
            if (isLogin) {
                data = await login(email, password);
            } else {
                if (!orgName.trim()) {
                    setError('Organization name is required');
                    setLoading(false);
                    return;
                }
                data = await register(email, password, orgName);
            }
            setToken(data.access_token);
            const { fetchMe } = await import('@/lib/api');
            const user = await fetchMe();
            localStorage.setItem('saarthi_user', JSON.stringify({
                id: user.id,
                email: user.email,
                org_id: (user as any).organization_id || (user as any).active_org_id,
                role: (user as any).role,
            }));
            router.push('/');
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Could not reach backend — make sure the API is running on port 8000');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-card">
                {/* Logo */}
                <div className="login-logo">
                    <div className="sidebar-logo-mark">
                        <Zap size={16} />
                    </div>
                    <span className="login-logo-text">Saarthi</span>
                </div>

                <p className="login-subtitle">Revenue Operating System</p>

                {/* Tabs */}
                <div className="login-tabs">
                    <button
                        className={`login-tab${isLogin ? ' active' : ''}`}
                        onClick={() => { setIsLogin(true); setError(''); }}
                        type="button"
                    >
                        Sign In
                    </button>
                    <button
                        className={`login-tab${!isLogin ? ' active' : ''}`}
                        onClick={() => { setIsLogin(false); setError(''); }}
                        type="button"
                    >
                        Register
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    {!isLogin && (
                        <div className="form-group">
                            <label className="input-label">
                                <Building2 size={13} style={{ display: 'inline', marginRight: 4 }} />
                                Organization Name
                            </label>
                            <input
                                className="input"
                                type="text"
                                placeholder="Acme Corp"
                                value={orgName}
                                onChange={e => setOrgName(e.target.value)}
                                required
                            />
                        </div>
                    )}

                    <div className="form-group">
                        <label className="input-label">
                            <Mail size={13} style={{ display: 'inline', marginRight: 4 }} />
                            Email Address
                        </label>
                        <input
                            className="input"
                            type="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                        />
                    </div>

                    <div className="form-group">
                        <label className="input-label">
                            <Lock size={13} style={{ display: 'inline', marginRight: 4 }} />
                            Password
                        </label>
                        <input
                            className="input"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            autoComplete={isLogin ? 'current-password' : 'new-password'}
                        />
                    </div>

                    {error && (
                        <div className="login-error">{error}</div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading}
                        style={{ marginTop: 8, height: 40 }}
                    >
                        {loading ? 'Please wait…' : (isLogin ? 'Sign In' : 'Create Account')}
                    </button>
                </form>
            </div>

            <style>{`
                .login-page {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--bg-base);
                    padding: 24px;
                }
                .login-card {
                    width: 100%;
                    max-width: 400px;
                    background: var(--bg-surface);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-xl);
                    padding: 36px 32px;
                }
                .login-logo {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 6px;
                }
                .login-logo-text {
                    font-size: 18px;
                    font-weight: 700;
                    color: var(--text-primary);
                    letter-spacing: -0.02em;
                }
                .login-subtitle {
                    font-size: 13px;
                    color: var(--text-muted);
                    margin-bottom: 28px;
                }
                .login-tabs {
                    display: flex;
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-md);
                    padding: 3px;
                    margin-bottom: 24px;
                }
                .login-tab {
                    flex: 1;
                    padding: 7px;
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--text-muted);
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    transition: background var(--transition-fast), color var(--transition-fast);
                }
                .login-tab.active {
                    background: var(--bg-surface);
                    color: var(--text-primary);
                    border: 1px solid var(--border);
                }
                .login-error {
                    font-size: 13px;
                    color: var(--danger);
                    background: rgba(239, 68, 68, 0.08);
                    border: 1px solid rgba(239, 68, 68, 0.2);
                    border-radius: var(--radius-md);
                    padding: 10px 12px;
                    margin-bottom: 12px;
                }
            `}</style>
        </div>
    );
}
