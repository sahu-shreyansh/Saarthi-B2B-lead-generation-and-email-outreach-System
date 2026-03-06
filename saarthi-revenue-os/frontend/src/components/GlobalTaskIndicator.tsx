"use client";

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

interface Task {
    id: string;
    task_name: string;
    status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILURE';
    progress: number;
}

export default function GlobalTaskIndicator() {
    const [activeTasks, setActiveTasks] = useState<Task[]>([]);
    const [isExpanded, setIsExpanded] = useState(false);

    useEffect(() => {
        // In a real app, this would use WebSockets or SSE.
        // For this implementation, we poll active tasks from localStorage 
        // where they were saved when initiated by other components.
        const pollTasks = async () => {
            const storedTaskIds = JSON.parse(localStorage.getItem('activePipelineTasks') || '[]');
            if (storedTaskIds.length === 0) {
                setActiveTasks([]);
                return;
            }

            const updatedTasks: Task[] = [];
            const completedIds: string[] = [];

            for (const id of storedTaskIds) {
                try {
                    const response = await api.get(`/tasks/${id}`);
                    const task = response.data;
                    updatedTasks.push(task);

                    if (task.status === 'SUCCESS' || task.status === 'FAILURE') {
                        completedIds.push(id);
                    }
                } catch (err) {
                    // If task polling fails, remove it so we don't block
                    completedIds.push(id);
                }
            }

            setActiveTasks(updatedTasks);

            // Clean up completed tasks from polling list after 5 seconds
            if (completedIds.length > 0) {
                setTimeout(() => {
                    const currentStored = JSON.parse(localStorage.getItem('activePipelineTasks') || '[]');
                    const remaining = currentStored.filter((id: string) => !completedIds.includes(id));
                    localStorage.setItem('activePipelineTasks', JSON.stringify(remaining));
                }, 5000);
            }
        };

        pollTasks();
        const intervalId = setInterval(pollTasks, 3000);
        return () => clearInterval(intervalId);
    }, []);

    if (activeTasks.length === 0) return null;

    const runningCount = activeTasks.filter(t => t.status === 'RUNNING' || t.status === 'PENDING').length;

    return (
        <div className="relative">
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-full hover:bg-surface-hover transition-colors"
            >
                {runningCount > 0 ? (
                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                ) : (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                )}
                <span className="text-sm font-medium text-text-primary">
                    {runningCount > 0 ? `${runningCount} Active Job${runningCount > 1 ? 's' : ''}` : 'All Jobs Complete'}
                </span>
            </button>

            {isExpanded && (
                <div className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-lg shadow-xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-border bg-background">
                        <h3 className="text-sm font-semibold text-text-primary">Pipeline Activity</h3>
                    </div>
                    <div className="max-h-64 overflow-y-auto p-2">
                        {activeTasks.map(task => (
                            <div key={task.id} className="p-3 mb-2 last:mb-0 rounded bg-background border border-border">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-sm font-medium text-text-primary truncate pr-4">
                                        {task.task_name.replace(/_/g, ' ')}
                                    </span>
                                    {task.status === 'RUNNING' && <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />}
                                    {task.status === 'SUCCESS' && <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />}
                                    {task.status === 'FAILURE' && <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                                    {task.status === 'PENDING' && <Clock className="w-4 h-4 text-text-muted shrink-0" />}
                                </div>

                                {/* Progress Bar */}
                                <div className="w-full bg-border rounded-full h-1.5 mb-1">
                                    <div
                                        className={`h-1.5 rounded-full ${task.status === 'FAILURE' ? 'bg-red-500' : task.status === 'SUCCESS' ? 'bg-green-500' : 'bg-primary transition-all duration-500'}`}
                                        style={{ width: `${task.progress}%` }}
                                    ></div>
                                </div>
                                <div className="flex justify-between text-xs text-text-muted">
                                    <span>{task.status}</span>
                                    <span>{task.progress}%</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
