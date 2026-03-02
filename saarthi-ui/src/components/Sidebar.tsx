'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
    Inbox, Send, Users, Activity, Settings, View, PhoneCall, AlignRight, BarChart3, Database, Target
} from 'lucide-react';
import Link from 'next/link';

export default function Sidebar() {
    const router = useRouter();
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    const mainLinks = [
        { icon: BarChart3, label: 'Dashboard', href: '/' },
        { icon: Target, label: 'Campaigns', href: '/campaigns' },
        { icon: Inbox, label: 'InboxHub', href: '/inbox' },
        { icon: Database, label: 'Lead Finder', href: '/lead-finder' },
        { icon: Send, label: 'Outreach', href: '/outreach' },
    ];

    const crmLinks = [
        { icon: Activity, label: 'Deal Pipeline', href: '/deal-pipeline' },
        { icon: View, label: 'Lists', href: '/lists' },
        { icon: Users, label: 'Accounts', href: '/accounts' },
        { icon: PhoneCall, label: 'Analytics', href: '/analytics' },
    ];

    const isActive = (href: string) => {
        if (href === '/') return pathname === '/';
        return pathname.startsWith(href);
    };

    const NavItem = ({ icon: Icon, label, href }: { icon: any, label: string, href: string }) => {
        const active = isActive(href);
        return (
            <Link href={href} style={{ textDecoration: 'none' }}>
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '8px 12px', marginBottom: 4,
                    borderRadius: 6, cursor: 'pointer',
                    color: active ? '#fff' : 'var(--text-secondary)',
                    background: active ? 'var(--bg-hover)' : 'transparent',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                }}>
                    {active && (
                        <div style={{
                            position: 'absolute', left: 0, top: '20%', bottom: '20%', width: 2,
                            background: 'var(--accent-primary)', borderRadius: '0 4px 4px 0',
                            boxShadow: '0 0 8px var(--accent-glow)'
                        }} />
                    )}
                    <Icon size={16} strokeWidth={active ? 2.5 : 2} style={{ color: active ? 'var(--accent-primary)' : 'inherit' }} />
                    {!collapsed && <span style={{ fontSize: 13, fontWeight: active ? 500 : 400 }}>{label}</span>}
                </div>
            </Link>
        );
    };

    return (
        <div style={{
            width: collapsed ? 68 : 240,
            height: '100vh',
            background: 'var(--bg-surface)',
            borderRight: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            transition: 'width 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
            position: 'relative',
            zIndex: 10,
        }}>
            {/* App Logo */}
            <div style={{
                padding: '24px 20px',
                display: 'flex', alignItems: 'center', gap: 12,
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: 16,
            }}>
                <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 0 15px var(--accent-glow)',
                    flexShrink: 0,
                }}>
                    <span style={{ color: '#000', fontWeight: 800, fontSize: 14 }}>S</span>
                </div>
                {!collapsed && (
                    <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                        Saarthi
                    </span>
                )}
            </div>

            <button
                onClick={() => setCollapsed(!collapsed)}
                style={{
                    position: 'absolute', top: 26, right: -12,
                    width: 24, height: 24, borderRadius: '50%',
                    background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', color: 'var(--text-secondary)', zIndex: 20,
                }}
            >
                <AlignRight size={12} />
            </button>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px' }}>
                <div style={{ marginBottom: 24 }}>
                    {!collapsed && <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0 12px', marginBottom: 8 }}>Core</div>}
                    {mainLinks.map(link => <NavItem key={link.href} {...link} />)}
                </div>

                <div style={{ marginBottom: 24 }}>
                    {!collapsed && <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0 12px', marginBottom: 8 }}>CRM</div>}
                    {crmLinks.map(link => <NavItem key={link.href} {...link} />)}
                </div>
            </div>

            <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border-subtle)' }}>
                <NavItem icon={Settings} label="Settings" href="/settings" />

                {/* User Card */}
                {!collapsed && (
                    <div style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '12px', marginTop: 8, borderRadius: 8,
                        background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)'
                    }}>
                        <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: '#fff', fontSize: 12, fontWeight: 600,
                        }}>
                            AS
                        </div>
                        <div style={{ overflow: 'hidden' }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Abhishek Sahu</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>abhishek@example.com</div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
