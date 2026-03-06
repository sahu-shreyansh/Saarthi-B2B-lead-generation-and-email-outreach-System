'use client';

import { usePathname } from 'next/navigation';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const NO_SHELL_ROUTES = ['/login', '/register'];

export default function LayoutShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    if (NO_SHELL_ROUTES.includes(pathname)) {
        return <>{children}</>;
    }

    return (
        <div className="app-shell">
            <Sidebar />
            <div className="main-area">
                <Topbar />
                <main className="page-content page-enter">
                    {children}
                </main>
            </div>
        </div>
    );
}
