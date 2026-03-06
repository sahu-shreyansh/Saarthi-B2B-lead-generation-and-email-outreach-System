import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { InboxThread, InboxMessage } from '@/types';

export function useInboxThreads(status?: string) {
    return useQuery({
        queryKey: ['inbox', 'threads', status],
        queryFn: async () => {
            const { data } = await api.get<InboxThread[]>('/inbox', { params: { status } });
            return data;
        }
    });
}

export function useInboxMessages(thread_id: string) {
    return useQuery({
        queryKey: ['inbox', 'thread', thread_id, 'messages'],
        queryFn: async () => {
            const { data } = await api.get<InboxMessage[]>(`/inbox/${thread_id}/messages`);
            return data;
        },
        enabled: !!thread_id
    });
}

export function useProcessInbox() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async () => {
            const { data } = await api.post<{ task_id: string }>('/inbox/process');
            return data;
        },
        onSuccess: () => {
            // Task kicks off, threads might update shortly. Ideal to use poller inside component.
            queryClient.invalidateQueries({ queryKey: ['inbox', 'threads'] });
        }
    });
}

export function useReplyToThread() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (thread_id: string) => {
            const { data } = await api.post<{ task_id: string }>(`/inbox/${thread_id}/reply`);
            return data;
        },
        onSuccess: (_, thread_id) => {
            queryClient.invalidateQueries({ queryKey: ['inbox', 'thread', thread_id, 'messages'] });
        }
    });
}

export function useClassifyThread() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (thread_id: string) => {
            const { data } = await api.post<{ task_id: string }>(`/inbox/${thread_id}/classify`);
            return data;
        },
        onSuccess: (_, thread_id) => {
            queryClient.invalidateQueries({ queryKey: ['inbox', 'threads'] });
            queryClient.invalidateQueries({ queryKey: ['inbox', 'thread', thread_id, 'messages'] });
        }
    });
}
