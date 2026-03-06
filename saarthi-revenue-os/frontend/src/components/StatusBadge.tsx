import { ReplyType, ReplyStatus, LeadStatus, FollowupStatus } from '@/lib/types';

type BadgeVariant = 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'purple';

function Badge({ variant, children }: { variant: BadgeVariant; children: React.ReactNode }) {
    return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function ReplyTypeBadge({ type }: { type: ReplyType | undefined }) {
    if (!type || type === 'EMPTY') return <span className="badge badge-gray">—</span>;
    const map: Record<string, BadgeVariant> = {
        POSITIVE: 'green',
        NEGATIVE: 'red',
        OOO: 'yellow',
        NEUTRAL: 'gray',
    };
    return <Badge variant={map[type] ?? 'gray'}>{type}</Badge>;
}

export function ReplyStatusBadge({ status }: { status: ReplyStatus | undefined }) {
    if (!status || status === '') return <span className="badge badge-gray">—</span>;
    return (
        <Badge variant={status === 'REPLIED' ? 'green' : 'gray'}>
            {status === 'REPLIED' ? '✓ Replied' : 'No Reply'}
        </Badge>
    );
}

export function LeadStatusBadge({ status }: { status: LeadStatus | undefined }) {
    if (!status) return null;
    const map: Record<string, BadgeVariant> = {
        NEW: 'blue',
        IN_SEQUENCE: 'purple',
        REPLIED: 'green',
        CLOSED: 'gray',
        PENDING: 'yellow',
        SENT: 'blue',
    };
    return <Badge variant={map[status] ?? 'gray'}>{status.replace('_', ' ')}</Badge>;
}

export function FollowupStatusBadge({ status }: { status: FollowupStatus | undefined }) {
    if (!status) return null;
    const map: Record<string, BadgeVariant> = {
        PENDING: 'yellow',
        SENT: 'blue',
        STOPPED: 'gray',
    };
    return <Badge variant={map[status] ?? 'gray'}>{status}</Badge>;
}
