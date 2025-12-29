import { useState } from 'react';
import { Button } from './ui'; // Input removed as unused
import { X, Send, Bug, Lightbulb } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import api from '../api';

interface FeedbackModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
    const [type, setType] = useState<'bug' | 'feature'>('bug');
    const [message, setMessage] = useState('');
    const [includeLogs, setIncludeLogs] = useState(true);
    const [sending, setSending] = useState(false);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async () => {
        if (!message.trim()) return;
        setSending(true);
        try {
            let logs = '';
            if (includeLogs) {
                // @ts-ignore
                logs = (window.consoleLogs || []).map((l: any) => JSON.stringify(l)).join('\n');
            }

            await api.post('/feedback', {
                type,
                message,
                logs: includeLogs ? logs : undefined,
                url: window.location.href
            });
            setSuccess(true);
            setTimeout(() => {
                onClose();
                setSuccess(false);
                setMessage('');
            }, 2000);
        } catch (e) {
            alert('Failed to send feedback');
        } finally {
            setSending(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="bg-white dark:bg-slate-900 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl border border-slate-100 dark:border-slate-800"
                    >
                        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
                            <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
                                {type === 'bug' ? <Bug size={18} className="text-red-500" /> : <Lightbulb size={18} className="text-brand-blue" />}
                                Feedback
                            </h3>
                            <button onClick={onClose} className="p-1 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full text-slate-400">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-4">
                            {success ? (
                                <div className="py-8 text-center text-emerald-500">
                                    <Send size={48} className="mx-auto mb-4" />
                                    <p className="font-bold">Sent! Thank you.</p>
                                </div>
                            ) : (
                                <>
                                    <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                                        <button
                                            onClick={() => setType('bug')}
                                            className={`flex-1 py-1.5 text-sm font-bold rounded-md transition-all ${type === 'bug' ? 'bg-white dark:bg-slate-700 shadow text-red-500' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                                        >
                                            Bug Report
                                        </button>
                                        <button
                                            onClick={() => setType('feature')}
                                            className={`flex-1 py-1.5 text-sm font-bold rounded-md transition-all ${type === 'feature' ? 'bg-white dark:bg-slate-700 shadow text-brand-blue' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                                        >
                                            Feature Request
                                        </button>
                                    </div>

                                    <textarea
                                        autoFocus
                                        value={message}
                                        onChange={e => setMessage(e.target.value)}
                                        placeholder={type === 'bug' ? "What happened? Steps to reproduce..." : "How can we improve VoiceBrain?"}
                                        className="w-full h-32 p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:ring-2 focus:ring-brand-blue outline-none text-slate-800 dark:text-slate-200 resize-none text-sm"
                                    />

                                    {type === 'bug' && (
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={includeLogs}
                                                onChange={e => setIncludeLogs(e.target.checked)}
                                                className="w-4 h-4 rounded text-brand-blue"
                                            />
                                            <span className="text-sm text-slate-500 dark:text-slate-400">Include console logs (last 50)</span>
                                        </label>
                                    )}

                                    <Button onClick={handleSubmit} disabled={!message.trim() || sending} className="w-full">
                                        {sending ? 'Sending...' : 'Submit Feedback'}
                                    </Button>
                                </>
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
