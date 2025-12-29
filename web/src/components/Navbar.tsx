import { Link } from 'react-router-dom';
import { Button } from './ui';
import { VoiceBrainLogo } from './VoiceBrainLogo';
import { useTheme } from '../context/ThemeContext';
import { Sun, Moon, Laptop, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export default function Navbar() {
    const { theme, setTheme } = useTheme();
    const [showThemeMenu, setShowThemeMenu] = useState(false);

    return (
        <nav className="fixed top-0 w-full z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/60 h-16">
            <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
                <div className="flex items-center gap-8">
                    <Link to="/" className="flex items-center gap-2">
                        <VoiceBrainLogo className="w-8 h-8 text-brand-blue" />
                        <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">VoiceBrain</span>
                    </Link>
                    <Link to="/pricing" className="text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Pricing
                    </Link>
                </div>
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <button
                            onClick={() => setShowThemeMenu(!showThemeMenu)}
                            className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-colors flex items-center gap-1"
                            title="Switch theme"
                        >
                            {theme === 'light' && <Sun size={18} />}
                            {theme === 'dark' && <Moon size={18} />}
                            {theme === 'system' && <Laptop size={18} />}
                            <ChevronDown size={14} className={`transition-transform duration-200 ${showThemeMenu ? 'rotate-180' : ''}`} />
                        </button>

                        {showThemeMenu && (
                            <>
                                <div className="fixed inset-0 z-40" onClick={() => setShowThemeMenu(false)} />
                                <div className="absolute right-0 mt-2 w-40 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-1 z-50 animate-in fade-in zoom-in duration-200">
                                    <button
                                        onClick={() => { setTheme('light'); setShowThemeMenu(false); }}
                                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${theme === 'light' ? 'bg-blue-50 dark:bg-blue-900/30 text-brand-blue' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                                    >
                                        <Sun size={16} /> Light
                                    </button>
                                    <button
                                        onClick={() => { setTheme('dark'); setShowThemeMenu(false); }}
                                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${theme === 'dark' ? 'bg-blue-50 dark:bg-blue-900/30 text-brand-blue' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                                    >
                                        <Moon size={16} /> Dark
                                    </button>
                                    <button
                                        onClick={() => { setTheme('system'); setShowThemeMenu(false); }}
                                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${theme === 'system' ? 'bg-blue-50 dark:bg-blue-900/30 text-brand-blue' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                                    >
                                        <Laptop size={16} /> System
                                    </button>
                                </div>
                            </>
                        )}
                    </div>

                    <Link to="/login" className="text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-brand-blue transition-colors">
                        Log In
                    </Link>
                    <Link to="/login">
                        <Button className="bg-slate-900 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 text-white hover:bg-slate-800 rounded-full px-5 h-9 text-sm shadow-lg shadow-slate-900/20 dark:shadow-none">
                            Get Started Free
                        </Button>
                    </Link>
                </div>
            </div>
        </nav>
    );
}
