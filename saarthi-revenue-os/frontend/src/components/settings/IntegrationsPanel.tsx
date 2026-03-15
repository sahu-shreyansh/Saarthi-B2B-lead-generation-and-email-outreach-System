'use client';

import React, { useState } from 'react';
import { useIntegrations } from '@/hooks/useIntegrations';
import { Zap, Shield, Key, CheckCircle, XCircle, Loader2, ChevronDown, Activity } from 'lucide-react';

export const IntegrationsPanel = () => {
    const { status, models, loading, modelsLoading, error, updateApify, updateSerpApi, updateOpenRouter, test } = useIntegrations();
    
    const [apifyKey, setApifyKey] = useState('');
    const [serpApiKey, setSerpApiKey] = useState('');
    const [openRouterKey, setOpenRouterKey] = useState('');
    const [selectedModel, setSelectedModel] = useState('');
    const [testResults, setTestResults] = useState<Record<string, { type: 'success' | 'error', message: string } | null>>({});

    const handleTest = async (provider: 'apify' | 'serpapi' | 'openrouter') => {
        setTestResults(prev => ({ ...prev, [provider]: null }));
        const res = await test(provider);
        setTestResults(prev => ({
            ...prev,
            [provider]: { type: res.success ? 'success' : 'error', message: res.message }
        }));
    };

    const usagePercent = status ? Math.min(100, (status.ai_usage_tokens / status.ai_usage_limit) * 100) : 0;
    const isOverLimit = usagePercent >= 100;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">

            {/* Platform Usage Bar (Only shown if NOT using own OpenRouter key) */}
            {!status?.openrouter && status && (
                <div className="p-6 bg-brand/[0.03] border border-brand/10 rounded-2xl">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Activity size={18} className="text-brand" />
                            <span className="font-semibold text-sm">Platform AI Quota (Free Tier)</span>
                        </div>
                        <span className="text-xs font-medium text-brand">
                            {status.ai_usage_tokens.toLocaleString()} / {status.ai_usage_limit.toLocaleString()} tokens
                        </span>
                    </div>
                    <div className="w-full h-2.5 bg-brand/10 rounded-full overflow-hidden mb-2">
                        <div 
                            className={`h-full transition-all duration-1000 ${isOverLimit ? 'bg-error' : 'bg-brand'}`}
                            style={{ width: `${usagePercent}%` }}
                        />
                    </div>
                    <p className="text-xs text-secondary">
                        {isOverLimit 
                            ? "You've exceeded the free-tier limit. Connect your OpenRouter key to continue using AI features."
                            : `You have ${Math.round(100 - usagePercent)}% of your free daily quota remaining.`}
                    </p>
                </div>
            )}

            {/* Providers Grid */}
            <div className="grid grid-cols-1 gap-6">
                
                {/* OpenRouter (LLM) */}
                <div className="p-6 bg-card border border-border rounded-2xl hover:border-brand/30 transition-colors">
                    <div className="flex items-start justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-brand/10 rounded-xl">
                                <Zap className="text-brand" size={22} />
                            </div>
                            <div>
                                <h3 className="font-bold text-lg">OpenRouter (Text & Intelligence)</h3>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                    {status?.openrouter ? (
                                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-success">
                                            <CheckCircle size={10} /> Connected
                                        </span>
                                    ) : (
                                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-secondary">
                                            <Shield size={10} /> Using Saarthi Default
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <button 
                            onClick={() => handleTest('openrouter')}
                            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-border hover:bg-hover transition-colors"
                        >
                            Test Connection
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div className="form-group">
                            <label className="input-label">OpenRouter API Key</label>
                            <div className="relative">
                                <Key className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={16} />
                                <input 
                                    type="password" 
                                    className="input pl-10" 
                                    placeholder="sk-or-v1-xxxxxxxx"
                                    value={openRouterKey}
                                    onChange={e => setOpenRouterKey(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label className="input-label">Default LLM Model</label>
                            <div className="relative">
                                <select 
                                    className="input appearance-none bg-transparent pr-10"
                                    value={selectedModel || status?.default_llm_model || ''}
                                    onChange={e => setSelectedModel(e.target.value)}
                                >
                                    <option value="">Select a model</option>
                                    {models.map(m => (
                                        <option key={m.id} value={m.id}>{m.name}</option>
                                    ))}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" size={16} />
                            </div>
                            <p className="text-[10px] text-muted mt-1.5 flex items-center gap-1">
                                <Zap size={10} className="text-brand" /> Recommended: anthropic/claude-3.5-sonnet
                            </p>
                        </div>

                        <button 
                            className="btn btn-primary w-full mt-2"
                            onClick={() => updateOpenRouter(openRouterKey, selectedModel)}
                            disabled={loading || !openRouterKey}
                        >
                            {loading ? <Loader2 className="animate-spin" size={18} /> : 'Save OpenRouter Settings'}
                        </button>
                    </div>

                    {testResults.openrouter && (
                        <div className={`mt-4 p-3 rounded-lg flex items-start gap-2 border ${testResults.openrouter.type === 'success' ? 'bg-success/10 border-success/20 text-success' : 'bg-error/10 border-error/20 text-error'}`}>
                            {testResults.openrouter.type === 'success' ? <CheckCircle size={16} className="mt-0.5" /> : <XCircle size={16} className="mt-0.5" />}
                            <span className="text-xs font-medium">{testResults.openrouter.message}</span>
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Apify (Maps & LinkedIn) */}
                    <div className="p-6 bg-card border border-border rounded-2xl hover:border-brand/30 transition-colors">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2.5 bg-success/10 rounded-xl">
                                <Activity className="text-success" size={22} />
                            </div>
                            <div>
                                <h3 className="font-bold">Apify (Lead Scraping)</h3>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                    {status?.apify ? (
                                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-success">
                                            <CheckCircle size={10} /> Connected
                                        </span>
                                    ) : (
                                        <span className="text-[10px] font-bold uppercase tracking-wider text-secondary">Disconnected</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="form-group">
                                <label className="input-label">Apify API Token</label>
                                <input 
                                    type="password" 
                                    className="input" 
                                    placeholder="apify_api_xxxxx"
                                    value={apifyKey}
                                    onChange={e => setApifyKey(e.target.value)}
                                />
                            </div>
                            <div className="flex gap-2 mt-2">
                                <button 
                                    className="btn btn-secondary flex-1 text-xs py-2"
                                    onClick={() => handleTest('apify')}
                                >
                                    Test
                                </button>
                                <button 
                                    className="btn btn-primary flex-1 text-xs py-2"
                                    onClick={() => updateApify(apifyKey)}
                                    disabled={loading || !apifyKey}
                                >
                                    {loading ? <Loader2 className="animate-spin" size={14} /> : 'Save'}
                                </button>
                            </div>
                        </div>

                        {testResults.apify && (
                            <div className={`mt-4 p-2.5 rounded-lg flex items-start gap-2 border ${testResults.apify.type === 'success' ? 'bg-success/10 border-success/20 text-success' : 'bg-error/10 border-error/20 text-error'}`}>
                                <span className="text-[11px] font-medium">{testResults.apify.message}</span>
                            </div>
                        )}
                    </div>

                    {/* SerpAPI (Google Search) */}
                    <div className="p-6 bg-card border border-border rounded-2xl hover:border-brand/30 transition-colors">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2.5 bg-yellow-500/10 rounded-xl">
                                <Shield className="text-yellow-600" size={22} />
                            </div>
                            <div>
                                <h3 className="font-bold">SerpAPI (Google)</h3>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                    {status?.serpapi ? (
                                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-success">
                                            <CheckCircle size={10} /> Connected
                                        </span>
                                    ) : (
                                        <span className="text-[10px] font-bold uppercase tracking-wider text-secondary">Disconnected</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="form-group">
                                <label className="input-label">SerpAPI Key</label>
                                <input 
                                    type="password" 
                                    className="input" 
                                    placeholder="serp_api_xxxxx"
                                    value={serpApiKey}
                                    onChange={e => setSerpApiKey(e.target.value)}
                                />
                            </div>
                            <div className="flex gap-2 mt-2">
                                <button 
                                    className="btn btn-secondary flex-1 text-xs py-2"
                                    onClick={() => handleTest('serpapi')}
                                >
                                    Test
                                </button>
                                <button 
                                    className="btn btn-primary flex-1 text-xs py-2"
                                    onClick={() => updateSerpApi(serpApiKey)}
                                    disabled={loading || !serpApiKey}
                                >
                                    {loading ? <Loader2 className="animate-spin" size={14} /> : 'Save'}
                                </button>
                            </div>
                        </div>

                        {testResults.serpapi && (
                            <div className={`mt-4 p-2.5 rounded-lg flex items-start gap-2 border ${testResults.serpapi.type === 'success' ? 'bg-success/10 border-success/20 text-success' : 'bg-error/10 border-error/20 text-error'}`}>
                                <span className="text-[11px] font-medium">{testResults.serpapi.message}</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {error && (
                <div className="p-4 bg-error/10 border border-error/20 rounded-xl text-error text-sm font-medium flex items-center gap-2">
                    <XCircle size={18} />
                    {error}
                </div>
            )}
        </div>
    );
};
