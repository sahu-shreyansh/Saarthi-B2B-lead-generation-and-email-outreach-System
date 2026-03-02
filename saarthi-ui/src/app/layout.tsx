import type { Metadata } from 'next';
import './globals.css';
import QueryProvider from '@/components/QueryProvider';
import LayoutShell from '@/components/LayoutShell';

export const metadata: Metadata = {
  title: 'Saarthi — AI Outreach SaaS',
  description: 'Thread-centric cold email outreach for modern sales teams',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{
        margin: 0,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        background: '#f8f9fc',
        color: '#1a1d2e',
        WebkitFontSmoothing: 'antialiased',
      }}>
        <QueryProvider>
          <LayoutShell>
            {children}
          </LayoutShell>
        </QueryProvider>
      </body>
    </html>
  );
}
