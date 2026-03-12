'use client';

import { useCampaign, useCampaignLeads, useUploadLeads } from '@/hooks/useCampaigns';
import { useParams, useRouter } from 'next/navigation';
import { Upload, ArrowLeft, Loader2, User, Mail, Building, Database, Sparkles, Activity } from 'lucide-react';
import { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { enrichLead } from '@/lib/api';
import { LeadIntelligenceModal } from '@/components/leads/LeadIntelligenceModal';


export default function CampaignLeadsPage() {
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();

    const { data: campaign, isLoading: loadingCamp } = useCampaign(id);
    const { data: leads = [], isLoading: loadingLeads } = useCampaignLeads(id);
    const uploadMutation = useUploadLeads();

    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploading, setUploading] = useState(false);

    // Intelligence Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
    const [selectedLeadName, setSelectedLeadName] = useState<string>('');

    // Enrichment Mutation
    const qc = useQueryClient();
    const enrichMut = useMutation({
        mutationFn: (leadId: string) => enrichLead(leadId),
        onSuccess: () => {
            alert('Bulk enrichment triggered successfully in the background.');
            qc.invalidateQueries({ queryKey: ['campaignLeads'] });
        },
        onError: (err: any) => alert('Failed to start enrichment: ' + (err.response?.data?.detail || err.message))
    });

    const handleBulkEnrich = () => {
        // Enriches the top 50 un-enriched leads in view as an example bulk action
        if (!leads.length) return;
        if (confirm(`Trigger AI enrichment on the first pending leads in this view?`)) {
            leads.slice(0, 10).forEach((l: any) => enrichMut.mutate(l.id)); // Limit to 10 for demo safety
        }
    };

    const openIntelligence = (lead: any) => {
        setSelectedLeadId(lead.id);
        const name = lead.first_name ? `${lead.first_name} ${lead.last_name || ''}` : lead.contact_name;
        setSelectedLeadName(name || lead.contact_email || 'Unknown');
        setIsModalOpen(true);
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        try {
            await uploadMutation.mutateAsync({ id, file });
            alert('Leads uploaded successfully');
        } catch (err: any) {
            alert('Upload failed: ' + (err.response?.data?.detail || err.message));
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    if (loadingCamp) return (
        <div className="p-8 flex items-center justify-center min-vh-50">
            <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
    );

    return (
        <div className="p-8 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.back()}
                        className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                        title="Back"
                    >
                        <ArrowLeft size={20} className="text-gray-400" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-white">{campaign?.name}</h1>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                {campaign?.status || 'Draft'}
                            </span>
                            <span className="text-sm text-gray-500 flex items-center gap-1">
                                <Database size={14} /> {leads.length} leads
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                        accept=".csv"
                    />
                    <button
                        className="btn btn-primary flex items-center gap-2"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                        {uploading ? 'Uploading...' : 'Upload CSV'}
                    </button>
                    <button
                        className="btn bg-[var(--bg-hover)] text-brand border border-brand/30 hover:bg-brand/10 transition-colors flex items-center gap-2"
                        onClick={handleBulkEnrich}
                        disabled={enrichMut.isPending || loadingLeads || leads.length === 0}
                    >
                        {enrichMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                        Enrich Leads
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="card-flat overflow-hidden border border-gray-800 bg-gray-900/20 backdrop-blur-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-gray-800 bg-gray-900/50">
                                <th className="p-4 font-semibold text-xs uppercase tracking-wider text-gray-400">Lead Contact</th>
                                <th className="p-4 font-semibold text-xs uppercase tracking-wider text-gray-400">Position & Company</th>
                                <th className="p-4 font-semibold text-xs uppercase tracking-wider text-gray-400">AI Score</th>
                                <th className="p-4 font-semibold text-xs uppercase tracking-wider text-gray-400">Status</th>
                                <th className="p-4 font-semibold text-xs uppercase tracking-wider text-gray-400">Sequence Stage</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {loadingLeads ? (
                                <tr>
                                    <td colSpan={4} className="p-12 text-center">
                                        <div className="flex flex-col items-center gap-3">
                                            <Loader2 size={24} className="animate-spin text-blue-500" />
                                            <span className="text-gray-500 animate-pulse">Fetching leads...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : leads.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="p-12 text-center">
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-gray-600">
                                                <Database size={24} />
                                            </div>
                                            <div className="max-w-xs mx-auto">
                                                <h3 className="text-white font-medium mb-1">No leads found</h3>
                                                <p className="text-sm text-gray-500 mb-6">Start by uploading a CSV file with your target prospects.</p>
                                                <button
                                                    className="btn btn-secondary btn-sm"
                                                    onClick={() => fileInputRef.current?.click()}
                                                >
                                                    Upload Now
                                                </button>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            ) : leads.map((lead: any) => (
                                <tr key={lead.id} className="hover:bg-white/[0.02] transition-colors group">
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
                                                <User size={16} />
                                            </div>
                                            <div>
                                                <div className="font-medium text-white">
                                                    {lead.first_name ? `${lead.first_name} ${lead.last_name || ''}` : (lead.contact_name || 'Anonymous')}
                                                </div>
                                                <div className="text-xs text-gray-500 flex items-center gap-1.5 mt-0.5">
                                                    <Mail size={12} className="text-gray-600" /> {lead.contact_email}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        <div className="flex flex-col">
                                            <span className="flex items-center gap-1.5 text-sm font-medium text-gray-300">
                                                <Building size={12} className="text-gray-500" /> {lead.company || lead.company_name || 'N/A'}
                                            </span>
                                            <span className="text-xs text-gray-500 italic mt-0.5">{lead.title || 'Decision Maker'}</span>
                                        </div>
                                    </td>

                                    {/* AI Score Column */}
                                    <td className="p-4">
                                        <button
                                            onClick={() => openIntelligence(lead)}
                                            className="group/score flex items-center gap-2 bg-[var(--bg-hover)] hover:bg-[#1f2937] border border-[var(--border)] rounded-full px-3 py-1 transition-all duration-200"
                                        >
                                            <span className={`font-bold font-heading text-sm ${lead.score >= 71 ? 'text-success' :
                                                    lead.score >= 41 ? 'text-warning' :
                                                        lead.score > 0 ? 'text-danger' : 'text-secondary'
                                                }`}>
                                                {lead.score > 0 ? lead.score : '--'}
                                            </span>
                                            <Activity size={12} className="text-brand opacity-70 group-hover/score:opacity-100" />
                                        </button>
                                    </td>

                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${lead.status === 'replied' || lead.status === 'interested'
                                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                            : lead.status === 'contacted'
                                                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                                : 'bg-gray-800 text-gray-400 border-gray-700'
                                            }`}>
                                            {lead.status}
                                        </span>
                                    </td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden max-w-[100px]">
                                                <div
                                                    className="h-full bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                                                    style={{ width: `${Math.min((lead.current_step_number || 0) * 25, 100)}%` }}
                                                />
                                            </div>
                                            <span className="text-[10px] font-medium text-gray-500">
                                                Step {lead.current_step_number || 0}
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <LeadIntelligenceModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                leadId={selectedLeadId}
                leadName={selectedLeadName}
            />
        </div>
    );
}
