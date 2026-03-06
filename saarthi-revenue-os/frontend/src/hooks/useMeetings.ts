import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Meeting } from '@/types';

export function useMeetings() {
    return useQuery({
        queryKey: ['meetings'],
        queryFn: async () => {
            const { data } = await api.get<Meeting[]>('/meetings');
            return data;
        }
    });
}

export function useCreateMeeting() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (payload: Partial<Meeting>) => {
            const { data } = await api.post<Meeting>('/meetings', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings'] });
        }
    });
}

export function useUpdateMeeting() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, ...payload }: Partial<Meeting> & { id: string }) => {
            const { data } = await api.patch<Meeting>(`/meetings/${id}`, payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings'] });
        }
    });
}

export function useDeleteMeeting() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/meetings/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['meetings'] });
        }
    });
}

export function useSendMeetingConfirmation() {
    return useMutation({
        mutationFn: async (id: string) => {
            const { data } = await api.post<{ task_id: string }>(`/meetings/${id}/send-confirmation`);
            return data;
        }
    });
}
