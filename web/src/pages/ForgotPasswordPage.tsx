import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { Button, Card } from '../components/ui';
import { Mail, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            await api.post('/auth/forgot-password', { email });
            setSubmitted(true);
        } catch (error: any) {
            // For security, we might not want to show precise errors, but for UX we often do.
            // Backend currently always returns success or "If this email..."
            setSubmitted(true);
        } finally {
            setIsLoading(false);
        }
    };

    if (submitted) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-white dark:bg-slate-900 p-8 rounded-2xl shadow-xl max-w-md w-full text-center space-y-6"
                >
                    <div className="mx-auto w-16 h-16 bg-blue-100 dark:bg-blue-900/30 text-brand-blue dark:text-blue-400 rounded-full flex items-center justify-center mb-4">
                        <Mail size={32} />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Check your inbox</h2>
                    <p className="text-slate-500 dark:text-slate-400">
                        If an account exists for <b className="text-slate-900 dark:text-white">{email}</b>, we sent a password reset link.
                    </p>
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg text-sm text-slate-400 dark:text-slate-500">
                        Top Tip (Demo): Check the backend console/logs for the reset link!
                    </div>
                    <Button variant="outline" onClick={() => navigate('/login')} className="w-full">
                        Back to Login
                    </Button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden bg-slate-50 dark:bg-slate-950">
            <div className="bg-noise" />
            <div className="bg-gradient-light" />

            <div className="absolute top-6 left-6">
                <button onClick={() => navigate('/login')} className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1">
                    ← Back to Login
                </button>
            </div>

            <div className="w-full max-w-md space-y-8 relative z-10">
                <div className="text-center space-y-2">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Reset Password</h1>
                    <p className="text-slate-500 dark:text-slate-400">Enter your email to receive recovery instructions.</p>
                </div>

                <Card className="border-slate-200 dark:border-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50">
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-1">
                            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase ml-1">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-3.5 text-slate-400" size={16} />
                                <input
                                    type="email"
                                    required
                                    placeholder="name@example.com"
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-10 py-3 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none transition-all"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <Button type="submit" disabled={isLoading} className="w-full group h-12 text-base">
                            {isLoading ? 'Sending...' : 'Send Reset Link'}
                            {!isLoading && <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />}
                        </Button>
                    </form>
                </Card>
            </div>
        </div>
    );
}
