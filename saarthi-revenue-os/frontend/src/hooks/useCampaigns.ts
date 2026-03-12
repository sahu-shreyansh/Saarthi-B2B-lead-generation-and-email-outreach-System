import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Campaign, CampaignEmail } from '@/types';

export function useCampaigns() {
    return useQuery({
        queryKey: ['campaigns'],
        queryFn: async () => {
            const { data } = await api.get<Campaign[]>('/campaigns');
            return data;
        }
    });
}

export function useCampaign(id: string) {
    return useQuery({
        queryKey: ['campaigns', id],
        queryFn: async () => {
            const { data } = await api.get<Campaign>(`/campaigns/${id}`);
            return data;
        },
        enabled: !!id
    });
}

export function useCreateCampaign() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (payload: Partial<Campaign>) => {
            const { data } = await api.post<Campaign>('/campaigns', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
        }
    });
}

export function useUpdateCampaign() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, ...payload }: Partial<Campaign> & { id: string }) => {
            const { data } = await api.patch<Campaign>(`/campaigns/${id}`, payload);
            return data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
            queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] });
        }
    });
}

export function useStartCampaign() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id: string) => {
            await api.post(`/campaigns/${id}/start`);
        },
        onSuccess: (_, id) => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
            queryClient.invalidateQueries({ queryKey: ['campaigns', id] });
        }
    });
}

export function usePauseCampaign() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id: string) => {
            await api.post(`/campaigns/${id}/pause`);
        },
        onSuccess: (_, id) => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
            queryClient.invalidateQueries({ queryKey: ['campaigns', id] });
        }
    });
}

export function useCampaignEmails(id: string) {
    return useQuery({
        queryKey: ['campaigns', id, 'emails'],
        queryFn: async () => {
            const { data } = await api.get<CampaignEmail[]>(`/campaigns/${id}/emails`);
            return data;
        },
        enabled: !!id
    });
}

export function useCampaignLeads(id: string) {
    return useQuery({
        queryKey: ['campaigns', id, 'leads'],
        queryFn: async () => {
            const { data } = await api.get<any[]>(`/leads?campaign_id=${id}`); // Reusing list_leads with filter
            return data;
        },
        enabled: !!id
    });
}

export function useUploadLeads() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, file }: { id: string; file: File }) => {
            const formData = new FormData();
            formData.append('file', file);
            const { data } = await api.post(`/campaigns/${id}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id, 'leads'] });
        }
    });
}

export function useCampaignSequence(id: string) {
    return useQuery({
        queryKey: ['campaigns', id, 'sequence'],
        queryFn: async () => {
            const { data } = await api.get<any>(`/campaigns/${id}/sequence`);
            return data;
        },
        enabled: !!id
    });
}

export function useUpdateCampaignSequence() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, ...payload }: { id: string; name: string; steps: any[] }) => {
            const { data } = await api.post(`/campaigns/${id}/sequence`, payload);
            return data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id, 'sequence'] });
        }
    });
}
