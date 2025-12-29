import { useState, useEffect } from 'react';
import { Tag, Trash2, Edit2, Check, X, Search, Filter, Hash } from 'lucide-react';
import api from '../api';
import { Button, Input } from './ui';

interface TagData {
    name: string;
    count: number;
}

export function TagManager() {
    const [tags, setTags] = useState<TagData[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [sortBy, setSortBy] = useState<'count' | 'name'>('count');
    const [editingTag, setEditingTag] = useState<string | null>(null);
    const [newName, setNewName] = useState('');

    useEffect(() => {
        fetchTags();
    }, []);

    const fetchTags = async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/tags');
            setTags(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleMerge = async (source: string, target: string) => {
        if (!target || source === target) {
            setEditingTag(null);
            return;
        }
        try {
            await api.put('/tags/merge', { source, target });
            setEditingTag(null);
            fetchTags();
        } catch (e) {
            alert("Failed to merge tags");
        }
    };

    const handleDelete = async (name: string) => {
        if (!confirm(`Are you sure you want to remove the tag "${name}" from all notes?`)) return;
        try {
            await api.delete(`/tags/${name}`);
            fetchTags();
        } catch (e) {
            alert("Failed to delete tag");
        }
    };

    const filteredTags = tags
        .filter(t => t.name.toLowerCase().includes(query.toLowerCase()))
        .sort((a, b) => {
            if (sortBy === 'count') return b.count - a.count;
            return a.name.localeCompare(b.name);
        });

    return (
        <div className="bg-white dark:bg-slate-900 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-soft overflow-hidden">
            <div className="p-8 border-b border-slate-50 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Tag className="text-brand-blue" size={24} /> Tag Manager
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Organize and refine your indexing system.</p>
                </div>

                <div className="flex items-center gap-2">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <Input
                            value={query}
                            onChange={(e: any) => setQuery(e.target.value)}
                            placeholder="Filter tags..."
                            className="pl-10 h-10 text-sm"
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSortBy(sortBy === 'count' ? 'name' : 'count')}
                        className="h-10 text-xs font-bold"
                    >
                        <Filter size={14} className="mr-2" />
                        {sortBy === 'count' ? 'Most Used' : 'Alphabetical'}
                    </Button>
                </div>
            </div>

            <div className="p-4 md:p-8">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-8 h-8 border-4 border-brand-blue border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm text-slate-400 font-medium">Loading tags...</span>
                    </div>
                ) : filteredTags.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="w-16 h-16 bg-slate-50 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-300 dark:text-slate-600">
                            <Tag size={32} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white text-center">No tags found</h3>
                        <p className="text-slate-500 dark:text-slate-400 text-center">Your notes don't have any tags yet.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredTags.map(tag => (
                            <div key={tag.name} className="group flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 rounded-2xl hover:border-brand-blue/30 dark:hover:border-brand-blue/30 hover:bg-white dark:hover:bg-slate-800 hover:shadow-sm transition-all">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="w-8 h-8 bg-white dark:bg-slate-900 rounded-lg flex items-center justify-center text-slate-400 dark:text-slate-500 border border-slate-100 dark:border-slate-800">
                                        <Hash size={14} />
                                    </div>
                                    {editingTag === tag.name ? (
                                        <input
                                            autoFocus
                                            value={newName}
                                            onChange={(e) => setNewName(e.target.value)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') handleMerge(tag.name, newName);
                                                if (e.key === 'Escape') setEditingTag(null);
                                            }}
                                            className="bg-transparent border-b-2 border-brand-blue outline-none text-sm font-bold text-slate-800 dark:text-slate-200 w-32"
                                        />
                                    ) : (
                                        <div className="overflow-hidden">
                                            <p className="font-bold text-slate-800 dark:text-slate-200 text-sm truncate">{tag.name}</p>
                                            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-widest">{tag.count} {tag.count === 1 ? 'note' : 'notes'}</p>
                                        </div>
                                    )}
                                </div>

                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    {editingTag === tag.name ? (
                                        <>
                                            <button onClick={() => handleMerge(tag.name, newName)} className="p-2 text-emerald-500 hover:bg-emerald-50 rounded-lg">
                                                <Check size={16} />
                                            </button>
                                            <button onClick={() => setEditingTag(null)} className="p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                                                <X size={16} />
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={() => { setEditingTag(tag.name); setNewName(tag.name); }}
                                                className="p-2 text-slate-400 hover:text-brand-blue hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                                title="Rename / Merge"
                                            >
                                                <Edit2 size={16} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(tag.name)}
                                                className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                                title="Delete"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
