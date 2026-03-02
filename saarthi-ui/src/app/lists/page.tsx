'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCampaigns, fetchLeads, importLeadsCSV } from '@/lib/api';
import { Search, Upload, Users, ListFilter, CheckCircle2, X } from 'lucide-react';

export default function ListsPage() {
    const qc = useQueryClient();
    const [search, setSearch] = useState('');
    const [showImport, setShowImport] = useState(false);
    const [importCampaign, setImportCampaign] = useState('');
    const [importFile, setImportFile] = useState<File | null>(null);

    const { data: campaigns = [], isLoading } = useQuery({
        queryKey: ['campaigns'],
        queryFn: fetchCampaigns,
    });

    const importMut = useMutation({
        mutationFn: (args: { file: File; campaign_id: string }) => importLeadsCSV(args.file, args.campaign_id),
        onSuccess: (data) => {
            alert(`Imported ${data.created} leads (${data.skipped} skipped)`);
            qc.invalidateQueries({ queryKey: ['campaigns'] });
            qc.invalidateQueries({ queryKey: ['leads'] });
            setShowImport(false);
            setImportFile(null);
            setImportCampaign('');
        },
        onError: (err: any) => alert(err?.response?.data?.detail || 'Import failed'),
    });

    const filtered = campaigns.filter((c: any) =>
        !search || c.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="page-container fade-in">
            <div className="page-header">
                <div>
                    <h1 className="page-title">Lists & Audiences</h1>
                    <p className="page-subtitle">
                        Manage your lead databases across {campaigns.length} campaigns
                    </p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowImport(true)}>
                    <Upload size={14} /> Import Leads (CSV)
                </button>
            </div>

            {/* Search */}
            <div style={{ position: 'relative', marginBottom: 24, maxWidth: 400 }}>
                <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                    value={search} onChange={e => setSearch(e.target.value)}
                    placeholder="Search by list or campaign name..."
                    style={{ width: '100%', paddingLeft: 40, background: 'var(--bg-surface)' }}
                />
            </div>

            {/* Table */}
            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>List Name (Campaign)</th>
                            <th>Status</th>
                            <th>Total Leads</th>
                            <th>Contacted</th>
                            <th>Reply Rate</th>
                            <th>Created Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Loading lists...</td></tr>
                        ) : filtered.length === 0 ? (
                            <tr><td colSpan={6} style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                                <ListFilter size={32} style={{ margin: '0 auto 16px', opacity: 0.2 }} />
                                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                                    {campaigns.length === 0 ? 'No lists available' : 'No matching lists'}
                                </p>
                                <p style={{ fontSize: 13, marginTop: 8 }}>
                                    {campaigns.length === 0 ? 'Create a campaign first to import leads into.' : 'Try adjusting your search query.'}
                                </p>
                            </td></tr>
                        ) : filtered.map((c: any, i: number) => (
                            <tr key={c.id} className="fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-sm)', background: 'rgba(20, 184, 166, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            <Users size={14} color="var(--accent-primary)" />
                                        </div>
                                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name} Leads</span>
                                    </div>
                                </td>
                                <td>
                                    <span className={`badge ${c.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                                        {c.status}
                                    </span>
                                </td>
                                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.leads_count ?? 0}</td>
                                <td>{c.total_sent ?? 0}</td>
                                <td>
                                    <span style={{ color: 'var(--success)', fontWeight: 700 }}>{c.reply_rate ?? 0}%</span>
                                </td>
                                <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Import Modal */}
            {showImport && (
                <div className="modal-overlay" onClick={() => setShowImport(false)}>
                    <div className="modal-content fade-in" onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                            <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Import Leads to List</h3>
                            <button onClick={() => setShowImport(false)} className="btn-ghost" style={{ padding: 4, borderRadius: '50%' }}>
                                <X size={18} />
                            </button>
                        </div>

                        <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', marginBottom: 24, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            Upload a standard CSV file. Must include <strong>name</strong> and <strong>email</strong> headers.
                            Optional fields: company, title, location, phone.
                        </div>

                        <div style={{ marginBottom: 20 }}>
                            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>Destination Campaign List *</label>
                            <select value={importCampaign} onChange={e => setImportCampaign(e.target.value)} style={{ width: '100%', padding: '12px', background: 'var(--bg-elevated)' }}>
                                <option value="">Select campaign to attach leads to...</option>
                                {campaigns.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                            </select>
                        </div>

                        <div style={{
                            border: '2px dashed var(--border-strong)', borderRadius: 'var(--radius-md)', padding: 40,
                            textAlign: 'center', marginBottom: 24, cursor: 'pointer',
                            background: importFile ? 'rgba(16, 185, 129, 0.05)' : 'var(--bg-surface)',
                            transition: 'all 0.2s'
                        }}
                            onMouseOver={e => e.currentTarget.style.borderColor = importFile ? 'var(--success)' : 'var(--accent-primary)'}
                            onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-strong)'}
                        >
                            <input type="file" accept=".csv" style={{ display: 'none' }} id="csvUpload"
                                onChange={e => setImportFile(e.target.files?.[0] || null)} />
                            <label htmlFor="csvUpload" style={{ cursor: 'pointer', display: 'block' }}>
                                {importFile ? (
                                    <CheckCircle2 size={36} color="var(--success)" style={{ margin: '0 auto 16px' }} />
                                ) : (
                                    <Upload size={36} color="var(--accent-primary)" style={{ margin: '0 auto 16px' }} />
                                )}
                                <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
                                    {importFile ? importFile.name : 'Click to select CSV file'}
                                </p>
                                {!importFile && <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>or drag and drop here</p>}
                            </label>
                        </div>

                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', paddingTop: 20, borderTop: '1px solid var(--border-subtle)' }}>
                            <button className="btn btn-secondary" onClick={() => setShowImport(false)}>Cancel</button>
                            <button className="btn btn-primary"
                                onClick={() => importFile && importCampaign && importMut.mutate({ file: importFile, campaign_id: importCampaign })}
                                disabled={!importFile || !importCampaign || importMut.isPending}>
                                {importMut.isPending ? 'Importing Leads...' : 'Start Import'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
