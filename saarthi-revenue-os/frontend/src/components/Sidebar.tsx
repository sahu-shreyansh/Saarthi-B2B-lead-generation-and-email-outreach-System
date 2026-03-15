'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
    LayoutDashboard,
    Users,
    Inbox,
    CheckSquare,
    BarChart3,
    Settings,
    Zap,
    CalendarDays,
    Search,
    BrainCircuit
} from 'lucide-react';
import { fetchMe } from '@/lib/api';

const NAV_LINKS = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/' },
    { icon: Search, label: 'Discovery', href: '/discovery' },
    { icon: Users, label: 'Leads', href: '/leads' },
    { icon: Zap, label: 'Campaigns', href: '/campaigns' },
    { icon: Inbox, label: 'Inbox', href: '/inbox' },
    { icon: CalendarDays, label: 'Meetings', href: '/meetings' },
    { icon: BrainCircuit, label: 'AI Agents', href: '/ai-agents' },
    { icon: Settings, label: 'Settings', href: '/settings' },
];

export default function Sidebar() {
    const pathname = usePathname();

    const { data: user } = useQuery({
        queryKey: ['me'],
        queryFn: fetchMe,
        staleTime: 5 * 60 * 1000,
        retry: false,
    });

    const isActive = (href: string) =>
        href === '/' ? pathname === '/' : pathname.startsWith(href);

    const credits = (user as any)?.credits_remaining ?? null;

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="sidebar-logo-mark">
                    <Zap size={14} />
                </div>
                <span className="sidebar-logo-text">Saarthi</span>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {NAV_LINKS.map(({ icon: Icon, label, href }) => {
                    const active = isActive(href);
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={`nav-item${active ? ' active' : ''}`}
                        >
                            <Icon size={15} strokeWidth={active ? 2.5 : 2} />
                            <span>{label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom Section */}
            <div className="sidebar-bottom">
                {/* Credit Balance */}
                <div className="credit-pill">
                    <Zap size={13} color="var(--accent-cyan)" />
                    <div className="flex-col" style={{ flex: 1 }}>
                        <span className="credit-pill-label">Credits</span>
                        <span className="credit-pill-value">
                            {credits !== null ? credits.toLocaleString() : '—'}
                        </span>
                    </div>
                </div>

                {/* User Row */}
                <div className="user-row">
                    <div className="user-avatar">
                        {user?.email?.charAt(0).toUpperCase() ?? 'U'}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="user-name">
                            {(user as any)?.organizations?.find(
                                (o: any) => o.id === (user as any)?.organization_id
                            )?.name ?? 'Organization'}
                        </div>
                        <div className="user-email">{user?.email ?? ''}</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
