'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { runDiscovery, fetchDiscoveryStatus } from '@/lib/api';
import { Search, MapPin, Target, Send, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export default function DiscoveryPage() {
    const [industry, setIndustry] = useState('');
    const [location, setLocation] = useState('');
    const [limit, setLimit] = useState(10);
    const [taskId, setTaskId] = useState<string | null>(null);

    const discoveryMutation = useMutation({
        mutationFn: runDiscovery,
        onSuccess: (data) => {
            setTaskId(data.task_id);
        },
        onError: (err: any) => {
            const msg = err.response?.data?.detail || err.message || 'Failed to start discovery';
            alert(`Error: ${msg}`);
        }
    });

    const { data: taskStatus, refetch: refetchStatus } = useQuery({
        queryKey: ['discoveryStatus', taskId],
        queryFn: () => fetchDiscoveryStatus(taskId!),
        enabled: !!taskId,
        refetchInterval: (query) => {
            const data = query.state.data as any;
            if (data?.status === 'COMPLETED' || data?.status === 'FAILED') {
                return false;
            }
            return 3000;
        },
    });

    const isRunning = taskId && taskStatus?.status !== 'COMPLETED' && taskStatus?.status !== 'FAILED';

    return (
        <div className="max-w-4xl mx-auto py-8">
            <div className="page-header mb-8">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                        Lead Discovery
                    </h1>
                    <p className="text-gray-400 mt-2">
                        Find real companies and decision makers using AI-powered search.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Form Card */}
                <div className="md:col-span-1">
                    <div className="card-flat p-6 space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Industry</label>
                            <div className="relative">
                                <Target className="absolute left-3 top-3 text-gray-500" size={16} />
                                <input
                                    type="text"
                                    className="input pl-10"
                                    placeholder="e.g. SaaS, Fintech"
                                    value={industry}
                                    onChange={(e) => setIndustry(e.target.value)}
                                    disabled={!!isRunning}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Location</label>
                            <div className="relative">
                                <MapPin className="absolute left-3 top-3 text-gray-500" size={16} />
                                <input
                                    type="text"
                                    className="input pl-10"
                                    placeholder="e.g. San Francisco, UK"
                                    value={location}
                                    onChange={(e) => setLocation(e.target.value)}
                                    disabled={!!isRunning}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">Max Leads</label>
                            <input
                                type="number"
                                className="input"
                                value={limit === 0 ? '' : limit}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value);
                                    setLimit(isNaN(val) ? 0 : val);
                                }}
                                min="1"
                                max="1000"
                                disabled={!!isRunning}
                            />
                        </div>

                        <button
                            className={`btn btn-primary w-full py-3 flex items-center justify-center gap-2 ${!!isRunning || !industry || !location ? 'opacity-50 cursor-not-allowed' : ''}`}
                            onClick={() => discoveryMutation.mutate({ industry, location, limit })}
                            disabled={!!isRunning || !industry || !location}
                        >
                            {isRunning ? (
                                <Loader2 className="animate-spin" size={18} />
                            ) : (
                                <Search size={18} />
                            )}
                            {isRunning ? 'Discovering...' : 'Find Leads'}
                        </button>
                    </div>
                </div>

                {/* Progress Card */}
                <div className="md:col-span-2">
                    <div className="card-flat p-6 h-full flex flex-col items-center justify-center text-center">
                        {!taskId ? (
                            <div className="space-y-4">
                                <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto">
                                    <Target className="text-blue-500" size={32} />
                                </div>
                                <h3 className="text-xl font-semibold">Ready to Discover</h3>
                                <p className="text-gray-400 max-w-xs">
                                    Enter an industry and location to start finding potential leads for your campaigns.
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-6 w-full">
                                {taskStatus?.status === 'COMPLETED' ? (
                                    <div className="space-y-4">
                                        <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto">
                                            <CheckCircle2 className="text-green-500" size={32} />
                                        </div>
                                        <h3 className="text-xl font-semibold">Discovery Complete!</h3>
                                        <p className="text-green-400">{taskStatus.result}</p>
                                        <button
                                            className="btn btn-secondary mt-4"
                                            onClick={() => window.location.href = '/leads'}
                                        >
                                            View Leads
                                        </button>
                                    </div>
                                ) : taskStatus?.status === 'FAILED' ? (
                                    <div className="space-y-4">
                                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto">
                                            <AlertCircle className="text-red-500" size={32} />
                                        </div>
                                        <h3 className="text-xl font-semibold text-red-500">Discovery Failed</h3>
                                        <p className="text-gray-400">{taskStatus.error_message}</p>
                                        <button
                                            className="btn btn-primary mt-4"
                                            onClick={() => setTaskId(null)}
                                        >
                                            Try Again
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-8 py-8 w-full max-w-sm mx-auto">
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="relative w-24 h-24">
                                                <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full"></div>
                                                <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
                                                <div className="absolute inset-0 flex items-center justify-center">
                                                    <span className="text-lg font-bold">{taskStatus?.progress || 0}%</span>
                                                </div>
                                            </div>
                                            <h3 className="text-xl font-semibold">Running Discovery...</h3>
                                            <p className="text-gray-400">Search results from Google & crawling company websites.</p>
                                        </div>

                                        <div className="w-full bg-gray-800 rounded-full h-2">
                                            <div
                                                className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                                                style={{ width: `${taskStatus?.progress || 0}%` }}
                                            ></div>
                                        </div>

                                        <div className="text-sm text-gray-500 animate-pulse">
                                            {taskStatus?.progress < 30 ? 'Searching Google...' :
                                                taskStatus?.progress < 70 ? 'Crawling company websites...' :
                                                    'Extracting decision makers...'}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
