'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Database, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { testDbConnection, connectExternalDb, disconnectExternalDb } from '@/lib/api';

interface DatabasePanelProps {
    currentConfig?: {
        mode: 'managed' | 'external';
        db_host?: string;
        db_port?: number;
        db_name?: string;
        db_user?: string;
    };
}

export function DatabasePanel({ currentConfig }: DatabasePanelProps) {
    const [mode, setMode] = useState<'managed' | 'external'>(currentConfig?.mode || 'managed');
    const [host, setHost] = useState(currentConfig?.db_host || '');
    const [port, setPort] = useState(currentConfig?.db_port || 5432);
    const [database, setDatabase] = useState(currentConfig?.db_name || '');
    const [user, setUser] = useState(currentConfig?.db_user || '');
    const [password, setPassword] = useState('');
    
    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'failed'>('idle');
    const [testError, setTestError] = useState('');

    const testMut = useMutation({
        mutationFn: testDbConnection,
        onMutate: () => {
            setTestStatus('testing');
            setTestError('');
        },
        onSuccess: () => setTestStatus('success'),
        onError: (err: any) => {
            setTestStatus('failed');
            setTestError(err.response?.data?.detail || 'Connection failed');
        }
    });

    const connectMut = useMutation({
        mutationFn: connectExternalDb,
        onSuccess: () => alert('Database connected successfully.'),
        onError: (err: any) => alert(err.response?.data?.detail || 'Failed to connect database')
    });

    const disconnectMut = useMutation({
        mutationFn: disconnectExternalDb,
        onSuccess: () => {
            setMode('managed');
            alert('Reverted to managed database.');
        },
        onError: () => alert('Failed to disconnect')
    });

    const handleTest = () => {
        testMut.mutate({ host, port: Number(port), database, user, password });
    };

    const handleSave = () => {
        if (mode === 'external') {
            connectMut.mutate({ host, port: Number(port), database, user, password });
        } else {
            disconnectMut.mutate();
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4">
                <div 
                    className={`p-4 border rounded-xl cursor-pointer transition-all ${mode === 'managed' ? 'border-brand bg-brand/5 shadow-sm' : 'border-border bg-card'}`}
                    onClick={() => setMode('managed')}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${mode === 'managed' ? 'border-brand' : 'border-secondary'}`}>
                            {mode === 'managed' && <div className="w-2 h-2 rounded-full bg-brand" />}
                        </div>
                        <div>
                            <p className="font-bold text-sm">Saarthi Managed Database</p>
                            <p className="text-xs text-secondary">Default multi-tenant isolation on our high-performance clusters.</p>
                        </div>
                    </div>
                </div>

                <div 
                    className={`p-4 border rounded-xl cursor-pointer transition-all ${mode === 'external' ? 'border-brand bg-brand/5 shadow-sm' : 'border-border bg-card'}`}
                    onClick={() => setMode('external')}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${mode === 'external' ? 'border-brand' : 'border-secondary'}`}>
                            {mode === 'external' && <div className="w-2 h-2 rounded-full bg-brand" />}
                        </div>
                        <div>
                            <p className="font-bold text-sm">Bring Your Own Database (BYODB)</p>
                            <p className="text-xs text-secondary">Connect your own PostgreSQL instance for full data sovereignty.</p>
                        </div>
                    </div>
                </div>
            </div>

            {mode === 'external' && (
                <div className="space-y-4 p-6 border border-dashed border-border rounded-2xl bg-hover/30 animate-in fade-in slide-in-from-top-2">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="form-group">
                            <label className="input-label">Host</label>
                            <input className="input" placeholder="db.example.com" value={host} onChange={e => setHost(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="input-label">Port</label>
                            <input className="input" type="number" placeholder="5432" value={port} onChange={e => setPort(Number(e.target.value))} />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="input-label">Database Name</label>
                        <input className="input" placeholder="saarthi_production" value={database} onChange={e => setDatabase(e.target.value)} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="form-group">
                            <label className="input-label">Username</label>
                            <input className="input" placeholder="postgres" value={user} onChange={e => setUser(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label className="input-label">Password</label>
                            <input className="input" type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} />
                        </div>
                    </div>

                    <div className="flex items-center gap-4 pt-2">
                        <button 
                            className="btn btn-secondary flex items-center gap-2" 
                            onClick={handleTest}
                            disabled={testMut.isPending}
                        >
                            {testMut.isPending ? <RefreshCw className="animate-spin" size={14} /> : <Database size={14} />}
                            Test Connection
                        </button>
                        
                        {testStatus === 'success' && (
                            <div className="flex items-center gap-2 text-success text-xs font-semibold">
                                <CheckCircle2 size={16} />
                                Connection Successful
                            </div>
                        )}
                        {testStatus === 'failed' && (
                            <div className="flex items-center gap-2 text-danger text-xs font-semibold">
                                <AlertCircle size={16} />
                                {testError}
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="pt-4 border-t border-border">
                <button 
                    className="btn btn-primary" 
                    onClick={handleSave}
                    disabled={connectMut.isPending || disconnectMut.isPending}
                >
                    {connectMut.isPending || disconnectMut.isPending ? 'Syncing...' : 'Apply Changes'}
                </button>
            </div>
        </div>
    );
}
