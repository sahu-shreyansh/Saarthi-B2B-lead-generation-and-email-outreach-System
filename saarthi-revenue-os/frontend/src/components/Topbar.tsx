'use client';

import { usePathname } from 'next/navigation';
import { Bell, Search } from 'lucide-react';
import GlobalTaskIndicator from './GlobalTaskIndicator';

const PAGE_TITLES: Record<string, string> = {
    '/': 'Dashboard',
    '/campaigns': 'Campaigns',
    '/leads': 'Leads',
    '/deal-pipeline': 'Pipeline',
    '/analytics': 'Analytics',
    '/settings': 'Settings',
};

export default function Topbar() {
    const pathname = usePathname();

    const title = Object.entries(PAGE_TITLES).find(([path]) =>
        path === '/' ? pathname === '/' : pathname.startsWith(path)
    )?.[1] ?? 'Saarthi';

    return (
        <header className="topbar">
            <div className="topbar-left">
                <span className="topbar-page-title">{title}</span>
            </div>

            <div className="topbar-right flex items-center gap-4">
                {/* Pipeline Task Tracker */}
                <GlobalTaskIndicator />

                {/* Global Search ⌘K */}
                <button
                    className="search-trigger"
                    onClick={() => {
                        const ev = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
                        document.dispatchEvent(ev);
                    }}
                    aria-label="Global search (⌘K)"
                >
                    <Search size={13} />
                    <span>Search</span>
                    <kbd className="kbd">⌘K</kbd>
                </button>

                {/* Notifications */}
                <button className="icon-btn" aria-label="Notifications">
                    <Bell size={16} />
                </button>
            </div>
        </header>
    );
}
