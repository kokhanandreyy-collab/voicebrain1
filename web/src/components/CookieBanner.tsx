import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Cookie } from 'lucide-react';

export function CookieBanner() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const consent = localStorage.getItem('cookie_consent');
        if (!consent) {
            // Small delay to not overwhelm immediate page load
            const timer = setTimeout(() => setIsVisible(true), 1000);
            return () => clearTimeout(timer);
        }
    }, []);

    const handleAccept = () => {
        localStorage.setItem('cookie_consent', 'true');
        setIsVisible(false);
    };

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ y: 100, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: 100, opacity: 0 }}
                    transition={{ duration: 0.5, type: 'spring' }}
                    className="fixed bottom-6 left-6 z-50 max-w-sm w-full"
                >
                    <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col gap-4">
                        <div className="flex items-start gap-4">
                            <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-full text-brand-blue">
                                <Cookie size={20} />
                            </div>
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                                    We use cookies
                                </p>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                                    We use cookies to ensure VoiceBrain works correctly and to improve your experience. Read our <Link to="/privacy" className="text-brand-blue hover:underline">Privacy Policy</Link>.
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={handleAccept}
                            className="w-full py-2.5 bg-brand-blue hover:bg-blue-600 text-white text-sm font-bold rounded-xl transition-colors"
                        >
                            Got it
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
