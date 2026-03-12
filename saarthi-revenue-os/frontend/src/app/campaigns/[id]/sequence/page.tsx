'use client';

import { useCampaign, useCampaignSequence, useUpdateCampaignSequence } from '@/hooks/useCampaigns';
import { useParams, useRouter } from 'next/navigation';
import { Plus, Trash2, Save, ArrowLeft, Clock, Loader2, Sparkles } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function SequenceBuilderPage() {
    const params = useParams();
    const id = params.id as string;
    const router = useRouter();

    const { data: campaign, isLoading: loadingCamp } = useCampaign(id);
    const { data: initialSequence, isLoading: loadingSeq } = useCampaignSequence(id);
    const updateMutation = useUpdateCampaignSequence();

    const [steps, setSteps] = useState<any[]>([]);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (initialSequence?.steps && initialSequence.steps.length > 0) {
            setSteps(initialSequence.steps);
        } else if (!loadingSeq && steps.length === 0) {
            // Add initial step if empty
            setSteps([{
                step_number: 1,
                step_type: 'email',
                wait_days: 1,
                template_subject: 'Quick question about {{company}}',
                template_body: 'Hi {{first_name}},\n\nI was looking at {{company}}'
            }]);
        }
    }, [initialSequence, loadingSeq]);

    const addStep = () => {
        const nextNum = steps.length + 1;
        setSteps([...steps, {
            step_number: nextNum,
            step_type: 'email',
            wait_days: 3,
            template_subject: `Follow up #${nextNum - 1}`,
            template_body: 'Hi {{first_name}},\n\nJust checking in...'
        }]);
    };

    const removeStep = (index: number) => {
        const newSteps = steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, step_number: i + 1 }));
        setSteps(newSteps);
    };

    const updateStep = (index: number, field: string, value: any) => {
        const newSteps = [...steps];
        newSteps[index] = { ...newSteps[index], [field]: value };
        setSteps(newSteps);
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateMutation.mutateAsync({
                id,
                name: campaign?.name || 'Sequence',
                steps
            });
            alert('Sequence saved successfully');
        } catch (err: any) {
            alert('Failed to save: ' + (err.response?.data?.detail || err.message));
        } finally {
            setSaving(false);
        }
    };

    if (loadingCamp || loadingSeq) return (
        <div className="p-8 flex items-center justify-center min-vh-50">
            <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
    );

    return (
        <div className="p-8 max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.back()}
                        className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <ArrowLeft size={20} className="text-gray-400" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-white">Sequence Builder</h1>
                        <p className="text-sm text-gray-500 mt-1">Flow for {campaign?.name}</p>
                    </div>
                </div>

                <button
                    className="btn btn-primary flex items-center gap-2"
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>

            {/* Steps List */}
            <div className="space-y-6">
                {steps.map((step, index) => (
                    <div key={index} className="relative">
                        {/* Connection Line */}
                        {index > 0 && (
                            <div className="absolute -top-6 left-10 w-0.5 h-6 bg-gray-800" />
                        )}

                        <div className="card-flat border border-gray-800 bg-gray-900/40 backdrop-blur-sm p-6 relative overflow-hidden group">
                            {/* Accent Glow */}
                            <div className="absolute -top-24 -right-24 w-48 h-48 bg-blue-500/5 blur-3xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

                            <div className="flex items-start justify-between mb-6">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 font-bold shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                                        {step.step_number}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h3 className="font-semibold text-white tracking-tight">Email #{step.step_number}</h3>
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-blue-500/70 bg-blue-500/5 px-2 py-0.5 rounded border border-blue-500/10">
                                                Active
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                                            <Clock size={12} className="text-gray-600" />
                                            {index === 0 ? 'Initial touchpoint' : `Wait ${step.wait_days} day(s) after previous step`}
                                        </div>
                                    </div>
                                </div>

                                {steps.length > 1 && (
                                    <button
                                        onClick={() => removeStep(index)}
                                        className="p-2 hover:bg-red-500/10 hover:text-red-500 text-gray-700 rounded-lg transition-all"
                                        title="Remove step"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                )}
                            </div>

                            <div className="space-y-5">
                                {index > 0 && (
                                    <div className="flex items-center gap-3 bg-gray-900/40 p-3 rounded-lg border border-gray-800">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Delay</label>
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="number"
                                                value={step.wait_days}
                                                onChange={(e) => updateStep(index, 'wait_days', Math.max(1, parseInt(e.target.value) || 1))}
                                                className="bg-gray-800 border-none rounded px-2 py-1 w-16 text-sm text-white focus:ring-1 focus:ring-blue-500"
                                                min={1}
                                            />
                                            <span className="text-xs text-gray-500">Days</span>
                                        </div>
                                    </div>
                                )}

                                <div>
                                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Subject Template</label>
                                    <input
                                        type="text"
                                        value={step.template_subject}
                                        onChange={(e) => updateStep(index, 'template_subject', e.target.value)}
                                        className="input w-full bg-gray-900/50 border-gray-800 focus:border-blue-500/50"
                                        placeholder="e.g. Question for {{first_name}}"
                                    />
                                </div>

                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Message Editor</label>
                                        <div className="flex gap-2">
                                            {['first_name', 'company', 'title'].map(tag => (
                                                <button
                                                    key={tag}
                                                    onClick={() => updateStep(index, 'template_body', step.template_body + ` {{${tag}}}`)}
                                                    className="text-[10px] font-bold bg-gray-800 hover:bg-gray-700 text-gray-400 px-2 py-0.5 rounded border border-gray-700 transition-colors"
                                                >
                                                    {'{{' + tag + '}}'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="relative group/editor">
                                        <textarea
                                            value={step.template_body}
                                            onChange={(e) => updateStep(index, 'template_body', e.target.value)}
                                            className="input w-full h-48 resize-none py-4 bg-gray-900/50 border-gray-800 focus:border-blue-500/50 leading-relaxed font-mono text-sm"
                                            placeholder="Write your email template... Use {{brackets}} for personalization."
                                        />
                                        <div className="absolute bottom-3 right-3">
                                            <button className="flex items-center gap-2 text-xs font-semibold bg-blue-500 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg shadow-lg shadow-blue-500/20 transition-all active:scale-95">
                                                <Sparkles size={14} /> AI Rewrite
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}

                <button
                    className="w-full py-6 border-2 border-dashed border-gray-800 rounded-2xl flex flex-col items-center justify-center gap-2 text-gray-500 hover:border-blue-500/40 hover:text-blue-400 hover:bg-blue-500/[0.02] transition-all group mt-8"
                    onClick={addStep}
                >
                    <div className="w-10 h-10 rounded-full bg-gray-800 group-hover:bg-blue-500/10 flex items-center justify-center transition-colors">
                        <Plus size={24} className="group-hover:scale-110 transition-transform" />
                    </div>
                    <span className="font-semibold text-sm tracking-tight">Add Sequential Follow-up</span>
                    <span className="text-xs text-gray-600">Automate your outreach with one more step</span>
                </button>
            </div>

            <div className="mt-12 p-6 border border-gray-800 rounded-2xl bg-gray-900/10">
                <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                    <Sparkles size={16} className="text-blue-400" /> Sequencing Best Practices
                </h3>
                <ul className="text-xs text-gray-500 space-y-2 list-disc list-inside">
                    <li>Optimal sequences usually have 4-6 steps over 14-21 days.</li>
                    <li>Always provide a clear "value prop" in the first 2 steps.</li>
                    <li>The "break-up" email (last step) often has the highest reply rate.</li>
                </ul>
            </div>
        </div>
    );
}
