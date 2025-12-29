import { useState, useEffect } from 'react';
import api from '../../api';
import { Bot, Save, RefreshCw, AlertCircle } from 'lucide-react';

interface SystemPrompt {
    key: string;
    text: string;
    version: number;
    updated_at: string;
}

export default function PromptsPage() {
    const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [editText, setEditText] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetchPrompts();
    }, []);

    const fetchPrompts = async () => {
        try {
            const { data } = await api.get('/admin/prompts');
            setPrompts(data);
            if (data.length > 0 && !selectedKey) {
                selectPrompt(data[0]);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const selectPrompt = (p: SystemPrompt) => {
        setSelectedKey(p.key);
        setEditText(p.text);
    };

    const handleSave = async () => {
        if (!selectedKey) return;
        setSaving(true);
        try {
            const { data } = await api.put(`/admin/prompts/${selectedKey}`, { text: editText });
            // Update list
            setPrompts(prompts.map(p => p.key === selectedKey ? data : p));
            alert('Prompt updated and cache active.');
        } catch (e) {
            alert('Failed to save prompt');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold dark:text-white flex items-center gap-2">
                    <Bot className="text-brand-blue" />
                    AI System Prompts
                </h1>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden">
                {/* List */}
                <div className="w-1/3 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-y-auto">
                    <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 font-bold text-xs uppercase text-slate-500">
                        Available Prompts
                    </div>
                    <div>
                        {prompts.map(p => (
                            <button
                                key={p.key}
                                onClick={() => selectPrompt(p)}
                                className={`w-full text-left p-4 border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${selectedKey === p.key ? 'bg-blue-50 dark:bg-slate-800 border-l-4 border-l-brand-blue' : ''}`}
                            >
                                <div className="font-bold text-slate-800 dark:text-slate-200">{p.key}</div>
                                <div className="text-xs text-slate-400 mt-1">v{p.version} • {new Date(p.updated_at).toLocaleDateString()}</div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Editor */}
                <div className="flex-1 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
                    {selectedKey ? (
                        <>
                            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50 dark:bg-slate-900">
                                <span className="font-mono font-bold text-brand-blue">{selectedKey}</span>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 bg-brand-blue hover:bg-blue-600 text-white rounded-lg font-bold shadow-lg shadow-blue-500/20 disabled:opacity-50"
                                >
                                    {saving ? <RefreshCw className="animate-spin" size={16} /> : <Save size={16} />}
                                    Save Changes
                                </button>
                            </div>
                            <div className="flex-1 p-0 relative">
                                <textarea
                                    value={editText}
                                    onChange={(e) => setEditText(e.target.value)}
                                    className="w-full h-full p-6 resize-none focus:outline-none bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-mono text-sm leading-relaxed"
                                    spellCheck={false}
                                />
                            </div>
                            <div className="p-2 text-xs text-center text-slate-400 bg-slate-50 dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
                                <AlertCircle size={10} className="inline mr-1" />
                                Changes take effect immediately but may be cached for up to 5 minutes.
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-400">
                            Select a prompt to edit
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
