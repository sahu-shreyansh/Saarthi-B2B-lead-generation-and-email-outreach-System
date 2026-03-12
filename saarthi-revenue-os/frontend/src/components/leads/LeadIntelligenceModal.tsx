import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getLeadScore, scoreLead, enrichLead } from '@/lib/api';
import { X, Loader2, Sparkles, RefreshCw, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

interface Factor {
    type: 'positive' | 'negative' | 'neutral';
    label: string;
}

interface ScoreData {
    score: number;
    factors: Factor[];
    confidence: number;
}

interface LeadIntelligenceModalProps {
    isOpen: boolean;
    onClose: () => void;
    leadId: string | null;
    leadName?: string;
}

export function LeadIntelligenceModal({ isOpen, onClose, leadId, leadName }: LeadIntelligenceModalProps) {
    const qc = useQueryClient();
    const [isPolling, setIsPolling] = useState(false);
    const [actionStatus, setActionStatus] = useState<{ message: string; type: 'info' | 'error' | 'success' } | null>(null);

    // Fetch Score Data
    const { data: scoreData, isLoading, error, refetch } = useQuery<ScoreData>({
        queryKey: ['lead-score', leadId],
        queryFn: () => getLeadScore(leadId!),
        enabled: isOpen && !!leadId,
        refetchInterval: isPolling ? 2000 : false,
        retry: 1, // Don't retry infinitely if no score exists yet
    });

    // Stop polling if we got a valid score structure or an explicit error
    useEffect(() => {
        if (isPolling && scoreData?.factors) {
            setIsPolling(false);
            setActionStatus({ message: 'Scoring completed successfully.', type: 'success' });
            setTimeout(() => setActionStatus(null), 3000);
            qc.invalidateQueries({ queryKey: ['campaignLeads'] }); // refresh table
        }
    }, [scoreData, isPolling, qc]);

    // Mutations
    const scoreMut = useMutation({
        mutationFn: () => scoreLead(leadId!),
        onSuccess: (data) => {
            setIsPolling(true);
            setActionStatus({ message: 'AI Scoring started...', type: 'info' });
        },
        onError: (err: any) => {
            setActionStatus({ message: err.response?.data?.detail || 'Failed to start scoring', type: 'error' });
        }
    });

    const enrichMut = useMutation({
        mutationFn: () => enrichLead(leadId!),
        onSuccess: (data) => {
            setActionStatus({ message: 'Enrichment pipeline started in background.', type: 'info' });
            setTimeout(() => setActionStatus(null), 4000);
        },
        onError: (err: any) => {
            setActionStatus({ message: err.response?.data?.detail || 'Failed to start enrichment', type: 'error' });
        }
    });

    if (!isOpen) return null;

    // Derived State
    const factorsArray = Array.isArray(scoreData?.factors) ? scoreData.factors : Object.values(scoreData?.factors || {});
    const hasData = factorsArray.length > 0;
    const isProcessing = isPolling || scoreMut.isPending || enrichMut.isPending;

    // Score Color Logic
    const getScoreColor = (score: number) => {
        if (score >= 71) return 'text-success border-success';
        if (score >= 41) return 'text-warning border-warning';
        return 'text-danger border-danger';
    };

    const positiveFactors = factorsArray.filter((f: any) => f.type === 'positive');
    const negativeFactors = factorsArray.filter((f: any) => f.type === 'negative');

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50 backdrop-blur-sm fade-in">
            <div className="w-full max-w-md h-full bg-[var(--bg-card)] border-l border-[var(--border)] shadow-xl flex flex-col slide-in-right">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[var(--border)]">
                    <div>
                        <h2 className="text-xl font-bold font-heading">AI Intelligence</h2>
                        <p className="text-sm text-secondary truncate max-w-[300px]">{leadName || 'Unknown Lead'}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-[var(--bg-hover)] rounded-full transition-colors">
                        <X size={20} className="text-secondary" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">

                    {/* Status Message */}
                    {actionStatus && (
                        <div className={`p-4 mb-6 rounded-lg border text-sm flex items-start gap-3 ${actionStatus.type === 'error' ? 'bg-danger/10 border-danger/20 text-danger' :
                            actionStatus.type === 'success' ? 'bg-success/10 border-success/20 text-success' :
                                'bg-[var(--bg-hover)] border-[var(--border)] text-primary'
                            }`}>
                            {actionStatus.type === 'info' ? <Loader2 size={16} className="animate-spin mt-0.5 shrink-0" /> :
                                actionStatus.type === 'error' ? <AlertTriangle size={16} className="mt-0.5 shrink-0" /> :
                                    <CheckCircle2 size={16} className="mt-0.5 shrink-0" />}
                            <span>{actionStatus.message}</span>
                        </div>
                    )}

                    {isLoading && !isPolling ? (
                        <div className="space-y-6">
                            <div className="skeleton h-40 w-full rounded-2xl"></div>
                            <div className="skeleton h-24 w-full rounded-xl"></div>
                            <div className="skeleton h-24 w-full rounded-xl"></div>
                        </div>
                    ) : (
                        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

                            {/* Score Visualization */}
                            <div className="flex flex-col items-center justify-center p-8 bg-[var(--bg-body)] rounded-2xl border border-[var(--border)]">
                                <div className={`relative flex items-center justify-center w-32 h-32 rounded-full border-4 ${hasData && scoreData ? getScoreColor(scoreData.score) : 'border-[var(--border)] text-muted'}`}>
                                    <span className="text-4xl font-bold font-heading">
                                        {hasData && scoreData ? scoreData.score : '--'}
                                    </span>
                                    {isPolling && (
                                        <div className="absolute inset-0 rounded-full border-4 border-t-brand animate-spin" style={{ borderRightColor: 'transparent', borderBottomColor: 'transparent', borderLeftColor: 'transparent' }}></div>
                                    )}
                                </div>
                                <h3 className="mt-4 font-semibold text-primary">AI Fit Score</h3>
                                {hasData && scoreData?.confidence !== undefined && (
                                    <p className="text-xs text-secondary mt-1">Confidence: {Math.round(scoreData.confidence * 100)}%</p>
                                )}
                                {!hasData && !isPolling && (
                                    <p className="text-sm text-secondary mt-2 text-center">No AI intelligence data available yet.</p>
                                )}
                            </div>

                            {/* Reasoning Factors */}
                            {hasData && (
                                <div className="space-y-6">
                                    {positiveFactors.length > 0 && (
                                        <div>
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-success mb-3 uppercase tracking-wider">
                                                <CheckCircle2 size={16} /> Positive Signals
                                            </h4>
                                            <ul className="space-y-2">
                                                {positiveFactors.map((f: any, i: number) => (
                                                    <li key={i} className="flex items-start gap-3 text-sm p-3 bg-success/5 border border-success/10 rounded-lg text-primary">
                                                        <span className="text-success select-none mt-0.5">✓</span>
                                                        <span>{f.label}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {negativeFactors.length > 0 && (
                                        <div>
                                            <h4 className="flex items-center gap-2 text-sm font-bold text-danger mb-3 uppercase tracking-wider">
                                                <AlertTriangle size={16} /> Negative Signals
                                            </h4>
                                            <ul className="space-y-2">
                                                {negativeFactors.map((f: any, i: number) => (
                                                    <li key={i} className="flex items-start gap-3 text-sm p-3 bg-danger/5 border border-danger/10 rounded-lg text-primary">
                                                        <span className="text-danger select-none mt-0.5">⚠</span>
                                                        <span>{f.label}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-[var(--border)] bg-[var(--bg-body)] grid grid-cols-2 gap-3">
                    <button
                        onClick={() => enrichMut.mutate()}
                        disabled={isProcessing}
                        className="btn bg-[var(--bg-hover)] text-primary border border-[var(--border)] hover:bg-[var(--border)] flex items-center justify-center gap-2"
                    >
                        {enrichMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} className="text-brand" />}
                        Enrich Data
                    </button>
                    <button
                        onClick={() => scoreMut.mutate()}
                        disabled={isProcessing}
                        className="btn btn-primary flex items-center justify-center gap-2"
                    >
                        {isPolling || scoreMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                        Re-Score Target
                    </button>
                </div>
            </div>
        </div>
    );
}
