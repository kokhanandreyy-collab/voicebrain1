import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Sparkles, Heart } from 'lucide-react';
import { Note, RelatedNote } from '../types';
import api from '../api';
import { ClarificationBubble } from './ClarificationBubble';

interface EditNoteModalProps {
    isOpen: boolean;
    onClose: () => void;
    note: Note | null;
    onSave: (updatedNote: Note) => void;
    onSelectRelated?: (noteId: string) => void;
}

export function EditNoteModal({ isOpen, onClose, note, onSave, onSelectRelated }: EditNoteModalProps) {
    const [title, setTitle] = useState('');
    const [summary, setSummary] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Related Notes State
    const [relatedNotes, setRelatedNotes] = useState<RelatedNote[]>([]);
    const [isLoadingRelated, setIsLoadingRelated] = useState(false);

    useEffect(() => {
        if (note) {
            setTitle(note.title || '');
            setSummary(note.summary || '');

            // Fetch related
            if (isOpen) {
                setIsLoadingRelated(true);
                api.get<RelatedNote[]>(`/notes/${note.id}/related`)
                    .then(({ data }) => setRelatedNotes(data))
                    .catch(err => console.error("Failed to fetch related notes", err))
                    .finally(() => setIsLoadingRelated(false));
            }
        }
    }, [note, isOpen]);

    const handleSave = async () => {
        if (!note) return;
        setIsSaving(true);
        try {
            const { data } = await api.put(`/notes/${note.id}`, {
                title,
                summary
            });
            onSave(data);
            onClose();
        } catch (error) {
            console.error("Failed to update note", error);
            alert("Failed to save changes.");
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen || !note) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-black/40 backdrop-blur-sm"
                    onClick={onClose}
                />
                <motion.div
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: 20 }}
                    className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]"
                >
                    <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800">
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">Edit Note</h3>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                            <X size={20} className="text-slate-500 dark:text-slate-400" />
                        </button>
                    </div>

                    <div className="p-6 space-y-6 overflow-y-auto">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Title</label>
                            <input
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none font-semibold text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500"
                                placeholder="Note Title"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Summary (Markdown)</label>
                            <div className="relative">
                                <textarea
                                    value={summary}
                                    onChange={(e) => setSummary(e.target.value)}
                                    className="w-full h-64 px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none font-mono text-sm text-slate-700 dark:text-slate-300 resize-none"
                                    placeholder="# Summary..."
                                />
                                <div className="absolute right-3 bottom-3 pointer-events-none">
                                    <Sparkles size={16} className="text-slate-400/50" />
                                </div>
                            </div>
                            <p className="text-xs text-slate-400">Editing re-calculates the AI embeddings for search.</p>
                        </div>

                        {/* Adaptive Learning Clarification */}
                        {note.action_items?.some(item => item.startsWith("Clarification Needed:")) && (
                            <ClarificationBubble
                                noteId={note.id}
                                question={note.action_items.find(i => i.startsWith("Clarification Needed:"))?.replace("Clarification Needed:", "").trim() || ""}
                            />
                        )}
                    </div>



                    {/* Apple Health Card */}
                    {note.health_data && (
                        <div className="mx-6 p-4 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/30 rounded-xl">
                            <div className="flex items-start justify-between">
                                <div className="flex gap-3">
                                    <div className="p-2 bg-red-100 dark:bg-red-900/40 rounded-lg text-red-600 dark:text-red-400">
                                        <Heart size={20} fill="currentColor" />
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-red-900 dark:text-red-200">Health Data Detected</h4>
                                        <div className="mt-1 text-sm text-red-700 space-y-1">
                                            {note.health_data.nutrition && (
                                                <p>🥗 {note.health_data.nutrition.name} ({note.health_data.nutrition.calories} kcal, {note.health_data.nutrition.protein}g protein)</p>
                                            )}
                                            {note.health_data.workout && (
                                                <p>🏃 {note.health_data.workout.type} ({note.health_data.workout.duration_minutes} min)</p>
                                            )}
                                            {note.health_data.symptoms && note.health_data.symptoms.length > 0 && (
                                                <p>🩺 Symptoms: {note.health_data.symptoms.join(', ')}</p>
                                            )}
                                            {note.health_data.trend_compliment && (
                                                <div className="mt-3 p-2 bg-green-100/50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-800 dark:text-green-300 flex items-center gap-2 font-medium animate-in fade-in slide-in-from-bottom-1">
                                                    <Sparkles size={14} className="text-green-600 dark:text-green-400" />
                                                    <span>{note.health_data.trend_compliment}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {/iPhone|iPad|iPod/.test(navigator.userAgent) && (
                                    <button
                                        onClick={() => {
                                            if (confirm("Please ensure you have installed the 'VoiceBrainHealth' Apple Shortcut from our guides before proceeding.\n\nOpen shortcut now?")) {
                                                const encoded = encodeURIComponent(JSON.stringify(note.health_data));
                                                window.location.href = `shortcuts://run-shortcut?name=VoiceBrainHealth&input=text&text=${encoded}`;
                                            }
                                        }}
                                        className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 text-sm font-medium rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors shadow-sm"
                                    >
                                        Save to Apple Health
                                    </button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Related Thoughts (Semantic Link) */}
                    <div className="mx-6 p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-900/30 rounded-xl space-y-3">
                        <div className="flex items-center gap-2 text-indigo-800 dark:text-indigo-300">
                            {/* Link Icon */}
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>
                            <h4 className="font-semibold text-sm">Related Thoughts</h4>
                        </div>

                        {isLoadingRelated ? (
                            <div className="text-xs text-indigo-500 animate-pulse">Finding connections...</div>
                        ) : relatedNotes.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {relatedNotes.map(rel => (
                                    <button
                                        key={rel.id}
                                        onClick={() => {
                                            // Quick Hack: Close and Re-open? Or just tell parent?
                                            // Ideally notify parent to switch note, but for now we might close or just navigate if we had routing.
                                            // Since we are in a modal controlled by parent, we can't easily switch unless we add a prop.
                                            // For this task, let's just alert or log, OR try to reload if we can.
                                            // Better: reload with this new note ID?
                                            // Actually, parent passes 'note' prop. We can't change it from here without a callback 'onSelectNote'.
                                            // Let's assume we can add 'onSelectNote' to props or valid just logging for now as "Switching not fully implemented in Modal architecture".
                                            // Wait, user asked for "Clicking one opens that note".
                                            // I should add `onSelectRelated?: (noteId: string) => void` to props.
                                            if (onSelectRelated) onSelectRelated(rel.id);
                                        }}
                                        className="text-left group flex items-start gap-2 p-2 bg-white dark:bg-slate-800 border border-indigo-100 dark:border-indigo-800 rounded-lg hover:shadow-md transition-all max-w-full"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate group-hover:text-brand-blue transition-colors">{rel.title}</p>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate w-40">{rel.summary || "No summary"}</p>
                                        </div>
                                        <div className="text-[9px] font-bold text-indigo-400 bg-indigo-50 dark:bg-indigo-900/50 px-1.5 py-0.5 rounded-full">
                                            {Math.round(rel.similarity * 100)}%
                                        </div>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-indigo-400 italic">No direct connections found.</p>
                        )}
                    </div>

                    <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3 bg-slate-50/50 dark:bg-slate-900/50">
                        <button
                            onClick={onClose}
                            className="px-6 py-2.5 rounded-xl text-slate-600 dark:text-slate-400 font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-6 py-2.5 rounded-xl bg-brand-blue text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {isSaving ? 'Saving...' : (
                                <>
                                    <Save size={18} /> Save Changes
                                </>
                            )}
                        </button>
                    </div>
                </motion.div>
            </div >
        </AnimatePresence >
    );
}
