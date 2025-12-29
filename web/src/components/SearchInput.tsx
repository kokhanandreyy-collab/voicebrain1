import { Mic, Search, Loader2, BrainCircuit } from 'lucide-react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchInputProps {
    value: string;
    onChange: (value: string) => void;
    isVoiceSearching: boolean;
    onStartVoice: () => void;
    onStopVoice: () => void;
    placeholder?: string;
    className?: string;
}

export function SearchInput({
    value,
    onChange,
    isVoiceSearching,
    onStartVoice,
    onStopVoice,
    placeholder = "Search (Semantic)...",
    className
}: SearchInputProps) {
    return (
        <div className={clsx("relative group", className)}>
            {/* Background Glow */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition duration-500" />

            <div className="relative bg-white flex items-center rounded-xl ring-1 ring-slate-200 shadow-sm group-focus-within:ring-2 group-focus-within:ring-brand-blue/50 group-focus-within:shadow-md transition-all">
                {/* Leading Icon */}
                <div className="pl-3 pr-2 text-slate-400">
                    <AnimatePresence mode="popLayout">
                        {value.length > 0 ? (
                            <motion.div
                                key="brain"
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                                className="text-brand-blue"
                            >
                                <BrainCircuit size={18} />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="search"
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                            >
                                <Search size={18} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={isVoiceSearching ? "Listening..." : placeholder}
                    disabled={isVoiceSearching}
                    className="flex-1 bg-transparent border-none outline-none py-3 text-sm text-slate-800 placeholder:text-slate-400"
                />

                {/* Trailing Voice Button */}
                <button
                    onClick={isVoiceSearching ? onStopVoice : onStartVoice}
                    className={clsx(
                        "mr-1.5 p-2 rounded-lg transition-all duration-300 relative overflow-hidden",
                        isVoiceSearching
                            ? "bg-red-50 text-red-500 hover:bg-red-100"
                            : "text-slate-400 hover:text-brand-blue hover:bg-blue-50"
                    )}
                    title={isVoiceSearching ? "Stop Recording" : "Voice Search"}
                >
                    <AnimatePresence mode="wait">
                        {isVoiceSearching ? (
                            <motion.div
                                key="listening"
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                            >
                                <Loader2 size={18} className="animate-spin" />
                                {/* Ripple Effect */}
                                <span className="absolute inset-0 rounded-lg bg-red-400/20 animate-ping" />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="mic"
                                initial={{ scale: 0.8, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.8, opacity: 0 }}
                            >
                                <Mic size={18} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </button>
            </div>

            {/* Keyboard Shortcut Hint (Optional) */}
            <div className="absolute right-14 top-1/2 -translate-y-1/2 hidden md:block pointer-events-none">
                {!value && !isVoiceSearching && (
                    <span className="text-[10px] font-bold text-slate-300 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">
                        CTRL+K
                    </span>
                )}
            </div>
        </div>
    );
}
