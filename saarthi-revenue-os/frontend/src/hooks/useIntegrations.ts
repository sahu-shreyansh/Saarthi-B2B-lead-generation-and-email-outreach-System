import { useState, useCallback, useEffect } from 'react';
import * as api from '../lib/api';

export interface IntegrationStatus {
    apify: boolean;
    serpapi: boolean;
    openrouter: boolean;
    default_llm_model: string;
    ai_usage_tokens: number;
    ai_usage_limit: number;
}

export interface ModelOption {
    id: string;
    name: string;
    context_length: number;
    pricing: {
        prompt: string;
        completion: string;
    };
}

export const useIntegrations = () => {
    const [status, setStatus] = useState<IntegrationStatus | null>(null);
    const [models, setModels] = useState<ModelOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [modelsLoading, setModelsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refreshStatus = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.fetchIntegrations();
            setStatus(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to fetch integrations');
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchModels = useCallback(async () => {
        setModelsLoading(true);
        try {
            const data = await api.fetchAvailableModels();
            setModels(data);
        } catch (err) {
            console.error('Failed to fetch models', err);
        } finally {
            setModelsLoading(false);
        }
    }, []);

    const updateApify = async (apiKey: string) => {
        setLoading(true);
        try {
            await api.saveApifyKey(apiKey);
            await refreshStatus();
            return { success: true };
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Failed to save Apify key';
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const updateSerpApi = async (apiKey: string) => {
        setLoading(true);
        try {
            await api.saveSerpApiKey(apiKey);
            await refreshStatus();
            return { success: true };
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Failed to save SerpAPI key';
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const updateOpenRouter = async (apiKey: string, model: string) => {
        setLoading(true);
        try {
            await api.saveOpenRouterSettings({ api_key: apiKey, default_model: model });
            await refreshStatus();
            return { success: true };
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Failed to save OpenRouter settings';
            return { success: false, error: msg };
        } finally {
            setLoading(false);
        }
    };

    const test = async (provider: 'apify' | 'serpapi' | 'openrouter') => {
        try {
            const res = await api.testIntegration(provider);
            return { success: res.status === 'ok', message: res.message };
        } catch (err: any) {
            return { success: false, message: err.response?.data?.detail || 'Test failed' };
        }
    };

    useEffect(() => {
        refreshStatus();
        fetchModels();
    }, [refreshStatus, fetchModels]);

    return {
        status,
        models,
        loading,
        modelsLoading,
        error,
        refreshStatus,
        updateApify,
        updateSerpApi,
        updateOpenRouter,
        test
    };
};
