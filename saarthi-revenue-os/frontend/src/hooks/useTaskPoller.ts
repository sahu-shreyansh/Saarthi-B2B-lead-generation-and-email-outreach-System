import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { AITask } from '@/types';

export function useTaskPoller(taskId: string | null, intervalMs: number = 3000) {
    return useQuery({
        queryKey: ['task', taskId],
        queryFn: async () => {
            const { data } = await api.get<AITask>(`/tasks/${taskId}`);
            return data;
        },
        enabled: !!taskId,
        refetchInterval: (query) => {
            const data = query.state?.data as AITask | undefined;
            if (data?.status === 'SUCCESS' || data?.status === 'FAILED' || data?.status === 'COMPLETED') {
                return false;
            }
            return intervalMs;
        }
    });
}
