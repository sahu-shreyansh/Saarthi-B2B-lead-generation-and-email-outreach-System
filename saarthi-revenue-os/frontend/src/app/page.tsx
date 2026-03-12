'use client';

import { useQuery } from '@tanstack/react-query';
import {
  Zap, Megaphone, Send, CalendarCheck,
  TrendingUp, TrendingDown, Minus, AlertCircle,
  User, Clock, Activity, MessageSquare,
  BarChart as BarChartIcon, LineChart as LineChartIcon
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  fetchMetrics, fetchRecentActivity, fetchLeadGrowth,
  fetchEmailPerformance, fetchRevenueMetrics
} from '@/lib/api';
import Link from 'next/link';
import { DashboardMetrics } from '@/types';

// ─── Skeleton helpers ─────────────────────────────────────────────────────────

function KpiSkeleton() {
  return (
    <div className="kpi-card">
      <div className="skeleton" style={{ height: 12, width: '60%', marginBottom: 16 }} />
      <div className="skeleton" style={{ height: 32, width: '50%', marginBottom: 10 }} />
      <div className="skeleton" style={{ height: 10, width: '40%' }} />
    </div>
  );
}

function ActivitySkeleton() {
  return (
    <div style={{ display: 'flex', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div className="skeleton" style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div className="skeleton" style={{ height: 11, width: '80%', marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 9, width: '40%' }} />
      </div>
    </div>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

interface KpiProps {
  label: string;
  value: string | number;
  delta?: string;
  positive?: boolean;
  icon: React.ElementType;
}

function KpiCard({ label, value, delta, positive, icon: Icon }: KpiProps) {
  return (
    <div className="kpi-card">
      <div className="flex items-center gap-1 mb-1" style={{ marginBottom: 12 }}>
        <Icon size={13} color="var(--text-muted)" />
        <span className="kpi-label">{label}</span>
      </div>
      <div className="kpi-value">{value}</div>
      {delta && (
        <div className={`kpi-delta ${positive ? 'positive' : positive === false ? 'negative' : 'neutral'}`}>
          {positive === true && <TrendingUp size={11} />}
          {positive === false && <TrendingDown size={11} />}
          {positive === undefined && <Minus size={11} />}
          <span>{delta}</span>
        </div>
      )}
    </div>
  );
}

// ─── Activity Feed ────────────────────────────────────────────────────────────

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  'lead_created': User,
  'reply_received': MessageSquare,
  'meeting_scheduled': CalendarCheck,
  'campaign_completed': Megaphone,
};

function PerformanceCharts({ leadGrowth, emailPerf, isLoading }: { leadGrowth: any[], emailPerf: any[], isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid-2" style={{ marginTop: 24, gap: 24 }}>
        <div className="card-flat" style={{ height: 300 }}><div className="skeleton w-full h-full" /></div>
        <div className="card-flat" style={{ height: 300 }}><div className="skeleton w-full h-full" /></div>
      </div>
    );
  }

  return (
    <div className="grid-2" style={{ marginTop: 24, gap: 24 }}>
      {/* Lead Growth Chart */}
      <div className="card-flat">
        <div className="flex items-center justify-between mb-6">
          <div className="section-title">Lead Growth (30d)</div>
          <LineChartIcon size={14} className="text-muted" />
        </div>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={leadGrowth}>
              <defs>
                <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(str) => {
                  const date = new Date(str);
                  return `${date.getMonth() + 1}/${date.getDate()}`;
                }}
              />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Area type="monotone" dataKey="count" stroke="var(--accent-primary)" fillOpacity={1} fill="url(#colorLeads)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Outreach Daily Trend Chart */}
      <div className="card-flat">
        <div className="flex items-center justify-between mb-6">
          <div className="section-title">Daily Outreach Trends</div>
          <Activity size={14} className="text-muted" />
        </div>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={emailPerf}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(str) => {
                  const date = new Date(str);
                  return `${date.getMonth() + 1}/${date.getDate()}`;
                }}
              />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Line type="monotone" dataKey="sent" stroke="var(--text-muted)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="opened" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="replied" stroke="var(--success)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-4 mt-4 justify-center">
          <div className="flex items-center gap-1.5 text-xs text-secondary"><div className="w-2.5 h-2.5 rounded-sm bg-[var(--text-muted)]" /> Sent</div>
          <div className="flex items-center gap-1.5 text-xs text-secondary"><div className="w-2.5 h-2.5 rounded-sm bg-[var(--accent-cyan)]" /> Opened</div>
          <div className="flex items-center gap-1.5 text-xs text-secondary"><div className="w-2.5 h-2.5 rounded-sm bg-[var(--success)]" /> Replied</div>
        </div>
      </div>
    </div>
  );
}

function ActivityFeed({ activities, isLoading }: { activities: any[], isLoading: boolean }) {
  return (
    <div className="card-flat" style={{ height: '100%' }}>
      <div className="section-title mb-2" style={{ marginBottom: 14 }}>Recent Activity</div>
      <div>
        {isLoading ? (
          [1, 2, 3, 4].map(i => <ActivitySkeleton key={i} />)
        ) : activities?.length ? (
          activities.map((a: any, i: number) => {
            const Icon = ACTIVITY_ICONS[a.type] ?? Activity;
            return (
              <div key={i} style={{
                display: 'flex',
                gap: 10,
                padding: '10px 0',
                borderBottom: i < activities.length - 1 ? '1px solid rgba(36,48,69,0.7)' : 'none',
                alignItems: 'flex-start',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'var(--bg-hover)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <Icon size={12} color="var(--text-muted)" />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 2 }}>{a.title}</div>
                  <div className="flex items-center gap-1" style={{ gap: 4 }}>
                    <Clock size={10} color="var(--text-muted)" />
                    <span className="text-meta">{new Date(a.timestamp).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-meta" style={{ padding: '20px 0', textAlign: 'center' }}>No recent activity.</div>
        )}
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: metrics, isLoading: isMetricsLoading, isError: isMetricsError, error: metricsError } = useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: fetchMetrics,
    refetchInterval: 60000,
  });

  const { data: activityList, isLoading: isActivityLoading } = useQuery({
    queryKey: ['dashboard', 'activity'],
    queryFn: () => fetchRecentActivity(10),
    refetchInterval: 60000,
  });

  const { data: leadGrowth, isLoading: isGrowthLoading } = useQuery({
    queryKey: ['dashboard', 'leadGrowth'],
    queryFn: () => fetchLeadGrowth(30),
  });

  const { data: emailPerf, isLoading: isPerfLoading } = useQuery({
    queryKey: ['dashboard', 'emailPerf'],
    queryFn: () => fetchEmailPerformance(30),
  });

  const { data: revenue, isLoading: isRevLoading, isError: isRevError, error: revError } = useQuery({
    queryKey: ['dashboard', 'revenue'],
    queryFn: fetchRevenueMetrics,
  });

  const m: DashboardMetrics = metrics || { total_leads: 0, qualified_leads: 0, active_campaigns: 0, emails_sent: 0, replies_received: 0, meetings_booked: 0, conversion_rate: 0 };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-left">
          <h1>Dashboard</h1>
          <p>Revenue operating system overview</p>
        </div>
      </div>

      {/* Backend Error Banner */}
      {(isMetricsError || isRevError) && (metricsError as any)?.response?.status !== 401 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          borderRadius: 'var(--radius-md)',
          padding: '10px 14px',
          marginBottom: 24,
          fontSize: 13,
          color: 'var(--danger)',
        }}>
          <AlertCircle size={15} />
          <span>
            Backend connectivity issue — ensure local services are running.
            {(metricsError as any)?.response?.status && ` (Status: ${(metricsError as any).response.status})`}
            {(!metricsError && (revError as any)?.response?.status) && ` (Status: ${(revError as any).response.status})`}
          </span>
        </div>
      )}

      {/* KPI Grid */}
      <div className="kpi-grid">
        {isMetricsLoading || isRevLoading ? (
          [1, 2, 3, 4, 5, 6, 7, 8].map(i => <KpiSkeleton key={i} />)
        ) : (
          <>
            <KpiCard
              label="Pipeline Value"
              value={`$${(revenue?.total_pipeline_value || 0).toLocaleString()}`}
              delta={`~${(revenue?.projected_revenue || 0).toLocaleString()} projected`}
              positive={true}
              icon={BarChartIcon}
            />
            <KpiCard
              label="AI Cost Savings"
              value={`$${(revenue?.ai_savings || 0).toLocaleString()}`}
              delta={`${revenue?.roi_multiplier}x ROI`}
              positive={true}
              icon={Zap}
            />
            <KpiCard
              label="Total Leads"
              value={m.total_leads.toLocaleString()}
              delta="All time"
              positive={undefined}
              icon={User}
            />
            <KpiCard
              label="Qualified Leads"
              value={m.qualified_leads.toLocaleString()}
              delta={`${m.total_leads > 0 ? Math.round(m.qualified_leads / m.total_leads * 100) : 0}% of total`}
              positive={m.qualified_leads > 0 ? true : undefined}
              icon={Zap}
            />
            <KpiCard
              label="Active Campaigns"
              value={m.active_campaigns.toLocaleString()}
              delta="Currently running"
              positive={undefined}
              icon={Megaphone}
            />
            <KpiCard
              label="Emails Sent"
              value={m.emails_sent.toLocaleString()}
              delta={`${m.replies_received} replies received`}
              positive={m.emails_sent > 0}
              icon={Send}
            />
            <KpiCard
              label="Meetings Booked"
              value={m.meetings_booked.toLocaleString()}
              delta="Total scheduled"
              positive={m.meetings_booked > 0 ? true : undefined}
              icon={CalendarCheck}
            />
            <KpiCard
              label="Conversion Rate"
              value={`${m.conversion_rate}%`}
              delta="Leads → Meetings"
              positive={m.conversion_rate > 0 ? true : undefined}
              icon={TrendingUp}
            />
          </>
        )}
      </div>

      {/* Performance Charts Row */}
      <PerformanceCharts
        leadGrowth={leadGrowth || []}
        emailPerf={emailPerf}
        isLoading={isGrowthLoading || isPerfLoading}
      />

      {/* Bottom Row: Activity Feed */}
      <div className="grid-2" style={{ marginTop: 24 }}>
        <ActivityFeed activities={activityList || []} isLoading={isActivityLoading} />
      </div>
    </div>
  );
}
