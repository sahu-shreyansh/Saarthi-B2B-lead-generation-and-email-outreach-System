'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { login, register } from '@/lib/api';
import { Mail, Lock, User, Building2, LogIn, UserPlus } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [companyName, setCompanyName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            let data;
            if (isLogin) {
                data = await login(email, password);
            } else {
                if (!fullName.trim()) { setError('Full name is required'); setLoading(false); return; }
                data = await register(email, password, fullName, companyName);
            }
            localStorage.setItem('saarthi_token', data.access_token);
            localStorage.setItem('saarthi_user', JSON.stringify({
                id: data.user_id,
                email: data.email,
                full_name: data.full_name || '',
                company_name: data.company_name || '',
            }));
            router.push('/');
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    const iconStyle: React.CSSProperties = {
        position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
    };

    return (
        <div style={{
            minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'linear-gradient(135deg, #f8f9fc 0%, #e8ecf8 50%, #f8f9fc 100%)',
        }}>
            <form onSubmit={handleSubmit} style={{
                width: 440, padding: '44px 40px', borderRadius: 20,
                background: '#fff', boxShadow: '0 8px 40px rgba(79,70,229,0.08)',
                border: '1px solid #e2e5f0',
            }}>
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1d2e', marginBottom: 4 }}>
                        Saarthi<span style={{ color: '#4F46E5' }}>.ai</span>
                    </h1>
                    <p style={{ color: '#9ca3b8', fontSize: 13 }}>AI-Powered Cold Email Outreach</p>
                </div>

                {/* Login / Register toggle */}
                <div style={{
                    display: 'flex', borderRadius: 10, overflow: 'hidden', marginBottom: 28,
                    border: '1px solid #e2e5f0', background: '#f8f9fc',
                }}>
                    <button type="button" onClick={() => setIsLogin(true)} style={{
                        flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                        background: isLogin ? '#4F46E5' : 'transparent',
                        color: isLogin ? '#fff' : '#5a6178',
                        fontSize: 13, fontWeight: 600,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                        borderRadius: isLogin ? 8 : 0,
                    }}>
                        <LogIn size={14} /> Sign In
                    </button>
                    <button type="button" onClick={() => setIsLogin(false)} style={{
                        flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                        background: !isLogin ? '#4F46E5' : 'transparent',
                        color: !isLogin ? '#fff' : '#5a6178',
                        fontSize: 13, fontWeight: 600,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                        borderRadius: !isLogin ? 8 : 0,
                    }}>
                        <UserPlus size={14} /> Register
                    </button>
                </div>

                {/* Registration fields */}
                {!isLogin && (
                    <>
                        <div style={{ position: 'relative', marginBottom: 16 }}>
                            <User size={15} color="#9ca3b8" style={iconStyle} />
                            <input type="text" placeholder="Full Name *" value={fullName}
                                onChange={e => setFullName(e.target.value)}
                                style={{ width: '100%', paddingLeft: 42 }} required />
                        </div>
                        <div style={{ position: 'relative', marginBottom: 16 }}>
                            <Building2 size={15} color="#9ca3b8" style={iconStyle} />
                            <input type="text" placeholder="Company Name" value={companyName}
                                onChange={e => setCompanyName(e.target.value)}
                                style={{ width: '100%', paddingLeft: 42 }} />
                        </div>
                    </>
                )}

                <div style={{ position: 'relative', marginBottom: 16 }}>
                    <Mail size={15} color="#9ca3b8" style={iconStyle} />
                    <input type="email" placeholder="Email" value={email}
                        onChange={e => setEmail(e.target.value)}
                        style={{ width: '100%', paddingLeft: 42 }} required />
                </div>
                <div style={{ position: 'relative', marginBottom: 24 }}>
                    <Lock size={15} color="#9ca3b8" style={iconStyle} />
                    <input type="password" placeholder="Password" value={password}
                        onChange={e => setPassword(e.target.value)}
                        style={{ width: '100%', paddingLeft: 42 }} required minLength={6} />
                </div>

                {error && (
                    <div style={{
                        marginBottom: 16, padding: '10px 14px', borderRadius: 8,
                        background: '#FEF2F2', border: '1px solid #FECACA', color: '#dc2626', fontSize: 12,
                    }}>
                        {error}
                    </div>
                )}

                <button type="submit" disabled={loading} className="btn btn-primary" style={{
                    width: '100%', padding: '12px', fontSize: 14, fontWeight: 600,
                    cursor: loading ? 'wait' : 'pointer',
                    opacity: loading ? 0.7 : 1,
                }}>
                    {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
                </button>
            </form>
        </div>
    );
}
