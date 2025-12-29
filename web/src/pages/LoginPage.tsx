import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { Button, Card, cn } from '../components/ui';
import { Mic, Lock, Mail, ArrowRight, Check, CheckCircle2, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { GoogleIcon, VkIcon, MailRuIcon, TwitterIcon } from '../components/SocialIcons';
import { motion, AnimatePresence } from 'framer-motion';

export default function LoginPage() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    // Check URL params for mode
    const [searchParams] = useSearchParams();

    useEffect(() => {
        if (searchParams.get('mode') === 'signup') {
            setIsLogin(false);
        }
    }, [searchParams]);

    // UI Enhancements
    const [showPassword, setShowPassword] = useState(false);
    const [confirmPassword, setConfirmPassword] = useState('');

    // UI States
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Password Validation
    const [validations, setValidations] = useState({
        length: false,
        digit: false,
        uppercase: false,
        special: false
    });

    useEffect(() => {
        setValidations({
            length: password.length >= 8,
            digit: /\d/.test(password),
            uppercase: /[A-Z]/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        });
    }, [password]);

    const isPasswordValid = Object.values(validations).every(Boolean);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            if (isLogin) {
                const { data } = await api.post('/auth/login', { email, password });
                localStorage.setItem('token', data.access_token);
                navigate('/dashboard');
            } else {
                if (!isPasswordValid) {
                    setError("Please meet all password requirements.");
                    setIsLoading(false);
                    return;
                }
                if (password !== confirmPassword) {
                    setError("Passwords do not match.");
                    setIsLoading(false);
                    return;
                }
                const { data } = await api.post('/auth/signup', { email, password });
                setSuccessMessage(data.message || "Registration successful! Please check your email.");
            }
        } catch (error: any) {
            console.error(error);
            setError(error.response?.data?.detail || "Something went wrong");
        } finally {
            setIsLoading(false);
        }
    };

    const handleOAuth = (provider: string) => {
        window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/${provider}/login`;
    };

    // Success Screen
    if (successMessage) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-white dark:bg-slate-900 p-8 rounded-2xl shadow-xl max-w-md w-full text-center space-y-6"
                >
                    <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-full flex items-center justify-center mb-4">
                        <CheckCircle2 size={32} />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Check your inbox</h2>
                    <p className="text-slate-500 dark:text-slate-400">{successMessage}</p>
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg text-sm text-slate-400 dark:text-slate-500">
                        Top Tip: Since this is a demo, check the detailed backend logs/console for the "Mock Email" link!
                    </div>
                    <Button variant="outline" onClick={() => setSuccessMessage(null)} className="w-full">
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
                <button onClick={() => navigate('/')} className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1">
                    ← Back home
                </button>
            </div>

            <div className="w-full max-w-md space-y-8 relative z-10">
                <div className="text-center space-y-2">
                    <motion.div
                        layoutId="logo"
                        className="mx-auto w-14 h-14 bg-brand-blue rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-500/25"
                    >
                        <Mic size={28} />
                    </motion.div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
                        {isLogin ? 'Welcome back' : 'Create an account'}
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400">Enter your details to access your workspace.</p>
                </div>

                <Card className="border-slate-200 dark:border-slate-800 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50">
                    <div className="grid grid-cols-2 gap-3 mb-6">
                        <div className="space-y-2">
                            <Button variant="outline" onClick={() => handleOAuth('google')} className="w-full justify-start pl-4 gap-3 text-xs font-semibold h-11 border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700">
                                <GoogleIcon className="w-5 h-5 flex-shrink-0" /> Google
                            </Button>
                            <Button variant="outline" onClick={() => handleOAuth('twitter')} className="w-full justify-start pl-4 gap-3 text-xs font-semibold h-11 border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700">
                                <TwitterIcon className="w-5 h-5 flex-shrink-0 text-black" /> X
                            </Button>
                        </div>
                        <div className="space-y-2">
                            <Button variant="outline" onClick={() => handleOAuth('mailru')} className="w-full justify-start pl-4 gap-3 text-xs font-semibold h-11 border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700">
                                <MailRuIcon className="w-5 h-5 flex-shrink-0 text-[#005FF9]" /> Mail.ru
                            </Button>
                            <Button variant="outline" onClick={() => handleOAuth('vk')} className="w-full justify-start pl-4 gap-3 text-xs font-semibold h-11 border-slate-300 hover:border-slate-400 hover:bg-slate-50 text-slate-700">
                                <VkIcon className="w-5 h-5 flex-shrink-0 text-[#0077FF]" /> VK ID
                            </Button>
                        </div>
                    </div>

                    <div className="relative mb-6">
                        <span className="absolute inset-0 flex items-center"><span className="w-full border-t border-slate-100 dark:border-slate-800" /></span>
                        <div className="relative flex justify-center text-xs uppercase"><span className="bg-white dark:bg-slate-900 px-2 text-slate-400 dark:text-slate-500 font-semibold tracking-wider">Or continue with</span></div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-500 dark:text-red-400 text-sm flex items-center gap-2">
                                <AlertCircle size={16} /> {error}
                            </div>
                        )}

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

                        <div className="space-y-1">
                            <div className="flex justify-between items-center px-1">
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Password</label>
                                {isLogin && (
                                    <button
                                        type="button"
                                        onClick={() => navigate('/forgot-password')}
                                        className="text-xs text-brand-blue hover:underline font-medium"
                                    >
                                        Forgot Password?
                                    </button>
                                )}
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-3 top-3.5 text-slate-400" size={16} />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    required
                                    placeholder="••••••••"
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-10 py-3 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none transition-all pr-10"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-3.5 text-slate-400 hover:text-slate-600 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        {/* Confirm Password (Signup Only) */}
                        <AnimatePresence>
                            {!isLogin && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="space-y-1"
                                >
                                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase ml-1">Confirm Password</label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-3.5 text-slate-400" size={16} />
                                        <input
                                            type={showPassword ? "text" : "password"}
                                            required={!isLogin}
                                            placeholder="••••••••"
                                            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-10 py-3 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none transition-all"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                        />
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Password Strength Indicators (only for signup) */}
                        <AnimatePresence>
                            {!isLogin && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="pt-2 grid grid-cols-2 gap-2"
                                >
                                    <ValidationItem isValid={validations.length} text="8+ characters" />
                                    <ValidationItem isValid={validations.digit} text="One number" />
                                    <ValidationItem isValid={validations.uppercase} text="Uppercase letter" />
                                    <ValidationItem isValid={validations.special} text="Special char (!@#)" />
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <Button type="submit" disabled={isLoading} className="w-full group h-12 text-base">
                            {isLoading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account')}
                            {!isLoading && <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />}
                        </Button>

                        {!isLogin && (
                            <p className="text-xs text-center text-slate-500 mt-4 px-4">
                                By signing up, you agree to our <a href="/terms" target="_blank" className="underline hover:text-brand-blue">Terms</a> and <a href="/privacy" target="_blank" className="underline hover:text-brand-blue">Privacy Policy</a>.
                            </p>
                        )}
                    </form>
                </Card>

                <div className="text-center text-sm">
                    <button
                        onClick={() => { setIsLogin(!isLogin); setError(null); }}
                        className="text-slate-500 dark:text-slate-400 hover:text-brand-blue transition-colors font-medium"
                    >
                        {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
                    </button>
                </div>
            </div>
        </div >
    );
}

function ValidationItem({ isValid, text }: { isValid: boolean; text: string }) {
    return (
        <div className={cn("flex items-center gap-1.5 text-xs transition-colors", isValid ? "text-green-600" : "text-slate-400")}>
            {isValid ? <Check size={12} strokeWidth={3} /> : <div className="w-3 h-3 rounded-full border border-slate-300" />}
            {text}
        </div>
    );
}
