import { Mic, Lightbulb, ClipboardList, ShoppingCart, MessageSquare, Plus } from 'lucide-react';
import { Button } from './ui';

interface EmptyStateProps {
    onSelectTemplate: (template: string) => void;
}

export function EmptyState({ onSelectTemplate }: EmptyStateProps) {
    const suggestions = [
        { label: "Morning Ideas", icon: <Lightbulb size={14} />, text: "I have an idea for a new feature..." },
        { label: "Meeting Recap", icon: <ClipboardList size={14} />, text: "Summary of our discussion today regarding..." },
        { label: "Shopping List", icon: <ShoppingCart size={14} />, text: "Groceries needed: milk, eggs, bread..." },
        { label: "Journal Entry", icon: <MessageSquare size={14} />, text: "Today I felt like..." },
    ];

    return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="relative mb-8">
                <div className="absolute inset-0 bg-blue-100 dark:bg-blue-900 rounded-full blur-3xl opacity-30 dark:opacity-20 animate-pulse" />
                <div className="relative w-24 h-24 bg-white dark:bg-slate-900 rounded-3xl shadow-xl dark:shadow-slate-950/50 flex items-center justify-center border border-slate-100 dark:border-slate-800 mb-6">
                    <Mic size={48} className="text-brand-blue" />
                    <div className="absolute -top-2 -right-2 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white shadow-lg border-2 border-white dark:border-slate-900">
                        <Plus size={16} />
                    </div>
                </div>
            </div>

            <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">Your brain is quiet.</h2>
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mb-10">
                Tap the microphone below to offload your thoughts, ideas, or reminders. We'll handle the rest.
            </p>

            <div className="w-full max-w-md">
                <p className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-widest mb-4">Start with a template</p>
                <div className="flex flex-wrap justify-center gap-3">
                    {suggestions.map((s, idx) => (
                        <button
                            key={idx}
                            onClick={() => onSelectTemplate(s.text)}
                            className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:border-brand-blue hover:text-brand-blue dark:hover:text-blue-400 hover:shadow-sm transition-all group"
                        >
                            <span className="text-slate-400 group-hover:text-brand-blue transition-colors">
                                {s.icon}
                            </span>
                            {s.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mt-12">
                <Button className="bg-brand-blue hover:bg-blue-600 text-white gap-2 px-8 py-6 rounded-2xl shadow-lg shadow-blue-200 dark:shadow-blue-900/20">
                    <Mic size={20} /> Start Recording
                </Button>
            </div>
        </div>
    );
}
