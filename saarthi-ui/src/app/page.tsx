'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchDashboard } from '@/lib/api';
import { Send, Users, BarChart3, Mail, TrendingUp, AlertTriangle } from 'lucide-react';

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  });

  const stats = [
    { label: 'Total Leads', value: data?.total_leads ?? 0, icon: Users, color: 'var(--accent-primary)', bg: 'rgba(20, 184, 166, 0.1)' },
    { label: 'Emails Sent', value: data?.total_sent ?? 0, icon: Send, color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)' },
    { label: 'Sent Today', value: data?.emails_sent_today ?? 0, icon: Mail, color: 'var(--accent-secondary)', bg: 'rgba(139, 92, 246, 0.1)' },
    { label: 'Replies Today', value: data?.replies_today ?? 0, icon: BarChart3, color: 'var(--success)', bg: 'rgba(16, 185, 129, 0.1)' },
    { label: 'Positive Replies', value: data?.positive_replies ?? 0, icon: TrendingUp, color: 'var(--warning)', bg: 'rgba(245, 158, 11, 0.1)' },
    { label: 'Followups Due', value: data?.followups_due ?? 0, icon: AlertTriangle, color: 'var(--danger)', bg: 'rgba(239, 68, 68, 0.1)' },
  ];

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Overview of your outreach performance</p>
        </div>
      </div>

      {isError && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)',
          padding: '16px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8,
          color: 'var(--danger)', fontSize: 13,
        }}>
          <AlertTriangle size={16} />
          <span>Could not reach backend — make sure the API is running on port 8000</span>
        </div>
      )}

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        {stats.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={i} className="card fade-in" style={{ padding: 20, animationDelay: `${i * 0.05}s`, display: 'flex', gap: 16, alignItems: 'center' }}>
              <div style={{
                width: 48, height: 48, borderRadius: 'var(--radius-md)', background: s.bg,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: `inset 0 0 0 1px ${s.color}40`,
              }}>
                <Icon size={24} color={s.color} />
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500, marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.03em' }}>
                  {isLoading ? '—' : s.value}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Usage Bar */}
      <div className="card" style={{ padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Monthly Email Usage</h3>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500, background: 'var(--bg-elevated)', padding: '4px 10px', borderRadius: 'var(--radius-sm)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>{data?.usage_sent ?? 0}</strong> / {data?.usage_limit ?? 100} emails
          </span>
        </div>

        <div style={{ width: '100%', height: 12, background: 'var(--bg-elevated)', borderRadius: 6, overflow: 'hidden', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)' }}>
          <div style={{
            width: `${Math.min(100, ((data?.usage_sent ?? 0) / (data?.usage_limit ?? 100)) * 100)}%`,
            height: '100%', borderRadius: 6,
            background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
            boxShadow: '0 0 10px var(--accent-glow)',
            transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
          }} />
        </div>
      </div>
    </div>
  );
}
