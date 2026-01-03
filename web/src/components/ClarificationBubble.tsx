import { useState } from 'react';
import { AlertTriangle, Send, Loader2, Check } from 'lucide-react';
import api from '../api';

interface ClarificationBubbleProps {
    noteId: string;
    question: string;
}

export function ClarificationBubble({ noteId, question }: ClarificationBubbleProps) {
    const [reply, setReply] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [hasReplied, setHasReplied] = useState(false);

    const handleSend = async (e: React.MouseEvent | React.KeyboardEvent) => {
        e.stopPropagation();
        if (!reply.trim()) return;
        setIsSending(true);
        try {
            await api.post(`/notes/${noteId}/reply`, { answer: reply });
            setHasReplied(true);
            setReply('');
        } catch (err) {
            console.error("Reply failed", err);
            alert("Failed to send reply");
        } finally {
            setIsSending(false);
        }
    };

    if (hasReplied) {
        return (
            <div className="mt-4 p-4 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-800 rounded-2xl flex items-center justify-between animate-in fade-in zoom-in duration-300">
                <p className="text-sm text-emerald-700 dark:text-emerald-400 font-medium">✨ Thank you! Adaptive memory updated.</p>
                <div className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                    <Check size={14} />
                </div>
            </div>
        );
    }

    return (
        <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-950/20 border border-orange-100 dark:border-orange-800 rounded-2xl space-y-3 animate-in fade-in slide-in-from-top-2 duration-500 shadow-sm" onClick={e => e.stopPropagation()}>
            <div className="flex items-start gap-2 text-orange-700 dark:text-orange-400">
                <AlertTriangle size={18} className="mt-0.5 shrink-0" />
                <div>
                    <p className="text-xs uppercase font-bold tracking-widest opacity-70 mb-1">Clarification Needed</p>
                    <p className="text-sm font-semibold leading-relaxed">{question}</p>
                </div>
            </div>

            <div className="flex gap-2 relative group">
                <input
                    type="text"
                    value={reply}
                    onChange={e => setReply(e.target.value)}
                    placeholder="Type your answer here..."
                    className="flex-1 px-4 py-2 text-sm bg-white dark:bg-slate-900 border border-orange-200 dark:border-orange-850 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/10 outline-none rounded-xl transition-all"
                    onKeyDown={e => e.key === 'Enter' && handleSend(e)}
                />
                <button
                    onClick={handleSend}
                    disabled={isSending || !reply.trim()}
                    className="p-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-xl transition-all shadow-md shadow-orange-500/20"
                >
                    {isSending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
            </div>
        </div>
    );
}
