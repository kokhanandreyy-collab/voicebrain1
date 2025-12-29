import { Link } from 'react-router-dom';

export default function Footer() {
    return (
        <footer className="py-8 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 z-10 relative">
            <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
                <p className="text-slate-400 dark:text-slate-500 text-sm">&copy; 2025 VoiceBrain. All rights reserved.</p>
                <div className="flex gap-6">
                    <Link to="/pricing" className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Pricing
                    </Link>
                    <Link to="/privacy" className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Privacy
                    </Link>
                    <Link to="/terms" className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Terms
                    </Link>
                    <Link to="/login" className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Sign In
                    </Link>
                </div>
            </div>
        </footer>
    );
}
