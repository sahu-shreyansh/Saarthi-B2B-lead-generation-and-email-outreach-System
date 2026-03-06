import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Lead } from '@/types';

export function useLeads(params?: { industry?: string; status?: string; search?: string; skip?: number; limit?: number; campaign_id?: string }) {
    return useQuery({
        queryKey: ['leads', params],
        queryFn: async () => {
            const { data } = await api.get<Lead[]>('/leads', { params });
            return data;
        }
    });
}

export function useLead(id: string) {
    return useQuery({
        queryKey: ['leads', id],
        queryFn: async () => {
            const { data } = await api.get<Lead>(`/leads/${id}`);
            return data;
        },
        enabled: !!id
    });
}

export function useCreateLead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (payload: Partial<Lead>) => {
            const { data } = await api.post<Lead>('/leads', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['leads'] });
        }
    });
}

export function useUpdateLead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, ...payload }: Partial<Lead> & { id: string }) => {
            const { data } = await api.patch<Lead>(`/leads/${id}`, payload);
            return data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['leads'] });
            queryClient.invalidateQueries({ queryKey: ['leads', variables.id] });
        }
    });
}

export function useDeleteLead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/leads/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['leads'] });
        }
    });
}
