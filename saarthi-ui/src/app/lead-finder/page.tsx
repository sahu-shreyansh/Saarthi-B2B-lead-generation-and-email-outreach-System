'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchCampaigns, createLead, generateLeads } from '@/lib/api';
import {
    Search, Users, Building2, MapPin, Briefcase, Plus, Database, Sparkles, UserPlus
} from 'lucide-react';

// Mock generation logic removed, using backend API now

export default function LeadFinderPage() {
    const qc = useQueryClient();

    const [jobTitle, setJobTitle] = useState('');
    const [industry, setIndustry] = useState('');
    const [location, setLocation] = useState('');

    const [results, setResults] = useState<any[]>([]);
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [isSearching, setIsSearching] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);

    const [showAddModal, setShowAddModal] = useState(false);
    const [addCampaign, setAddCampaign] = useState('');
    const [adding, setAdding] = useState(false);

    const { data: campaigns = [] } = useQuery({ queryKey: ['campaigns'], queryFn: fetchCampaigns });

    const handleSearch = async () => {
        if (!jobTitle && !industry) {
            alert('Please enter a Job Title or Industry to search.');
            return;
        }
        setIsSearching(true);
        setSelected(new Set());
        try {
            const res = await generateLeads({ job_title: jobTitle, industry, location, num_leads: 15 });
            const leadsWithIds = (res.leads || []).map((l: any, i: number) => ({ ...l, id: `generated-${Date.now()}-${i}` }));
            setResults(leadsWithIds);
            setHasSearched(true);
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to generate leads. Check backend logs or API keys.');
        } finally {
            setIsSearching(false);
        }
    };

    const toggleSelect = (id: string) => {
        const next = new Set(selected);
        next.has(id) ? next.delete(id) : next.add(id);
        setSelected(next);
    };

    const toggleAll = () => {
        if (selected.size === results.length) setSelected(new Set());
        else setSelected(new Set(results.map((l: any) => l.id)));
    };

    const addToCampaign = async () => {
        if (!addCampaign) { alert('Please select a campaign'); return; }
        setAdding(true);
        try {
            const selectedLeads = results.filter((l: any) => selected.has(l.id));
            for (const lead of selectedLeads) {
                await createLead({
                    campaign_id: addCampaign,
                    name: lead.name,
                    email: lead.email,
                    company: lead.company,
                    title: lead.title,
                    location: lead.location,
                    email_status: lead.email_status,
                });
            }
            // Remove added leads from results view
            setResults(prev => prev.filter(l => !selected.has(l.id)));
            qc.invalidateQueries({ queryKey: ['leads'] });
            setSelected(new Set());
            setShowAddModal(false);
        } catch (err: any) {
            alert(err?.response?.data?.detail || 'Failed to add leads');
        } finally { setAdding(false); }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
            {/* Left Box: Search Filter Engine */}
            <div style={{
                width: 320, background: 'var(--bg-surface)', borderRight: '1px solid var(--border-subtle)',
                display: 'flex', flexDirection: 'column',
            }}>
                <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                        <Database size={18} color="var(--accent-primary)" />
                        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>Lead Explorer</h2>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Find highly targeted prospects</p>
                </div>

                <div style={{ flex: 1, overflow: 'auto', padding: '24px 20px' }}>
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                            <Briefcase size={12} /> Job Title
                        </label>
                        <input
                            value={jobTitle} onChange={e => setJobTitle(e.target.value)}
                            placeholder="e.g. VP of Sales, Founder"
                            style={{ width: '100%' }}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                        />
                    </div>

                    <div style={{ marginBottom: 20 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                            <Building2 size={12} /> Industry
                        </label>
                        <input
                            value={industry} onChange={e => setIndustry(e.target.value)}
                            placeholder="e.g. Software, Banking"
                            style={{ width: '100%' }}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                        />
                    </div>

                    <div style={{ marginBottom: 24 }}>
                        <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                            <MapPin size={12} /> Location
                        </label>
                        <input
                            value={location} onChange={e => setLocation(e.target.value)}
                            placeholder="e.g. Mumbai, New York"
                            style={{ width: '100%' }}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                        />
                    </div>

                    <button
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '12px', fontSize: 14 }}
                        onClick={handleSearch}
                        disabled={isSearching}
                    >
                        {isSearching ? 'Scanning Web...' : <><Sparkles size={16} /> Generate Leads</>}
                    </button>

                    <div style={{ marginTop: 24, padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(20, 184, 166, 0.05)', border: '1px solid rgba(20, 184, 166, 0.1)' }}>
                        <p style={{ fontSize: 12, color: 'var(--accent-primary)', lineHeight: 1.6 }}>
                            <strong>Note:</strong> Enter criteria and click 'Generate'. The system will simulate finding B2B prospects matching your ICP to add to campaigns.
                        </p>
                    </div>
                </div>
            </div>

            {/* Right: Results View */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 32 }}>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                    <h1 className="page-title">Discovered Prospects</h1>
                    {selected.size > 0 && (
                        <div className="fade-in" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                <strong style={{ color: 'var(--accent-primary)' }}>{selected.size}</strong> selected
                            </span>
                            <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
                                <UserPlus size={14} /> Add to Campaign
                            </button>
                        </div>
                    )}
                </div>

                {isSearching ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                        <div style={{
                            width: 60, height: 60, borderRadius: '50%', border: '3px solid var(--border-subtle)',
                            borderTopColor: 'var(--accent-primary)', animation: 'spin 1s linear infinite', marginBottom: 24
                        }} />
                        <h3 style={{ fontSize: 16, color: 'var(--text-primary)', marginBottom: 8 }}>Searching database...</h3>
                        <p style={{ fontSize: 13 }}>Applying AI filters for {jobTitle || 'all titles'} in {location || 'global'}...</p>
                        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
                    </div>
                ) : !hasSearched ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                        <Search size={48} strokeWidth={1} style={{ marginBottom: 20, opacity: 0.3 }} />
                        <h3 style={{ fontSize: 18, color: 'var(--text-primary)', marginBottom: 8 }}>Ready to start prospecting</h3>
                        <p style={{ fontSize: 13, maxWidth: 300, textAlign: 'center', lineHeight: 1.6 }}>
                            Use the filters on the left to define your Ideal Customer Profile (ICP) and start generating high-quality leads.
                        </p>
                    </div>
                ) : results.length === 0 ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                        No leads found. Try broadening your search criteria.
                    </div>
                ) : (
                    <div className="table-container fade-in" style={{ flex: 1, overflow: 'auto' }}>
                        <table>
                            <thead>
                                <tr>
                                    <th style={{ width: 48, textAlign: 'center' }}>
                                        <input type="checkbox" checked={selected.size === results.length && results.length > 0} onChange={toggleAll} />
                                    </th>
                                    <th>Prospect</th>
                                    <th>Status</th>
                                    <th>Title</th>
                                    <th>Company</th>
                                    <th>Location</th>
                                </tr>
                            </thead>
                            <tbody>
                                {results.map((lead: any) => (
                                    <tr key={lead.id} style={{ background: selected.has(lead.id) ? 'rgba(20, 184, 166, 0.05)' : undefined }}>
                                        <td style={{ textAlign: 'center' }}>
                                            <input type="checkbox" checked={selected.has(lead.id)} onChange={() => toggleSelect(lead.id)} />
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, color: 'var(--accent-primary)', border: '1px solid var(--border-subtle)' }}>
                                                    {lead.name.charAt(0)}
                                                </div>
                                                <div>
                                                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{lead.name}</div>
                                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{lead.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{
                                                fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 4, textTransform: 'uppercase',
                                                background: lead.email_status === 'valid' ? 'rgba(34, 197, 94, 0.1)' : lead.email_status === 'invalid' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(234, 179, 8, 0.1)',
                                                color: lead.email_status === 'valid' ? '#22c55e' : lead.email_status === 'invalid' ? '#ef4444' : '#eab308'
                                            }}>
                                                {lead.email_status || 'unknown'}
                                            </span>
                                        </td>
                                        <td>{lead.title}</td>
                                        <td>{lead.company}</td>
                                        <td style={{ color: 'var(--text-secondary)' }}>{lead.location}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Modal */}
            {showAddModal && (
                <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16 }}>
                            Save {selected.size} Prospects
                        </h3>
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
                            Select a campaign to add these leads to. They will be officially added to your database and ready for outreach.
                        </p>

                        <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>Target Campaign</label>
                        <select value={addCampaign} onChange={e => setAddCampaign(e.target.value)}
                            style={{ width: '100%', marginBottom: 24 }}>
                            <option value="">Select campaign...</option>
                            {campaigns.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>

                        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                            <button className="btn btn-ghost" onClick={() => setShowAddModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={addToCampaign} disabled={adding || !addCampaign}>
                                {adding ? 'Saving...' : 'Save to Campaign'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
