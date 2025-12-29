import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Brain, Check, FileText, Mic, ArrowRight, CheckCircle } from 'lucide-react';
import { Button, Input } from './ui';
import api from '../api';

interface OnboardingModalProps {
    isOpen: boolean;
    onComplete: (user: any) => void;
}

export function OnboardingModal({ isOpen, onComplete }: OnboardingModalProps) {
    const [step, setStep] = useState(1);
    const [name, setName] = useState('');
    const [role, setRole] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    if (!isOpen) return null;

    const handleNext = () => setStep(step + 1);

    const handleFinish = async () => {
        setIsSaving(true);
        try {
            const { data } = await api.patch('/auth/me', {
                full_name: name,
                role: role,
                has_onboarded: true
            });
            onComplete(data);
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    const steps = [
        {
            title: "Welcome to VoiceBrain",
            subtitle: "Let's calibrate your AI for the best results.",
            icon: <Sparkles className="text-brand-blue" size={32} />,
            content: (
                <div className="space-y-4 py-4">
                    <div className="space-y-2 text-left">
                        <label className="text-sm font-bold text-slate-700 dark:text-slate-300">What's your name?</label>
                        <Input
                            value={name}
                            onChange={(e: any) => setName(e.target.value)}
                            placeholder="Alex Smith"
                            className="h-12 rounded-xl"
                        />
                    </div>
                    <div className="space-y-2 text-left">
                        <label className="text-sm font-bold text-slate-700 dark:text-slate-300">What's your role?</label>
                        <Input
                            value={role}
                            onChange={(e: any) => setRole(e.target.value)}
                            placeholder="Product Manager, Student, Artist..."
                            className="h-12 rounded-xl"
                        />
                    </div>
                </div>
            )
        },
        {
            title: "Connect your Brain",
            subtitle: "Sync your thoughts directly to your favorite apps.",
            icon: <Brain className="text-purple-500" size={32} />,
            content: (
                <div className="grid grid-cols-1 gap-3 py-4">
                    <button className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-800 rounded-2xl hover:border-brand-blue hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all text-left group">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-black dark:bg-slate-800 rounded-lg flex items-center justify-center text-white">
                                <FileText size={20} />
                            </div>
                            <div>
                                <p className="font-bold text-slate-800 dark:text-slate-200">Notion</p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">Sync notes & documents</p>
                            </div>
                        </div>
                        <ArrowRight size={16} className="text-slate-300 dark:text-slate-600 group-hover:text-brand-blue" />
                    </button>
                    <button className="flex items-center justify-between p-4 border border-slate-200 dark:border-slate-800 rounded-2xl hover:border-brand-blue hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all text-left group">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white">
                                <CheckCircle size={20} />
                            </div>
                            <div>
                                <p className="font-bold text-slate-800 dark:text-slate-200">Todoist</p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">Capture action items</p>
                            </div>
                        </div>
                        <ArrowRight size={16} className="text-slate-300 dark:text-slate-600 group-hover:text-brand-blue" />
                    </button>
                </div>
            )
        },
        {
            title: "Ready for Launch",
            subtitle: "You're all set. Try recording your first note now.",
            icon: <Mic className="text-emerald-500" size={32} />,
            content: (
                <div className="py-8 flex flex-col items-center">
                    <div className="w-20 h-20 bg-emerald-50 dark:bg-emerald-900/20 rounded-full flex items-center justify-center text-emerald-500 mb-4 animate-bounce">
                        <Check size={40} />
                    </div>
                    <p className="text-slate-600 dark:text-slate-300 text-sm max-w-[240px]">
                        Speak naturally. We'll transcribe, summarize, and categorize everything for you.
                    </p>
                </div>
            )
        }
    ];

    const currentStep = steps[step - 1];

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 dark:bg-black/70 backdrop-blur-sm p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className="bg-white dark:bg-slate-900 w-full max-w-md rounded-[32px] shadow-2xl dark:shadow-slate-950/50 overflow-hidden"
            >
                <div className="p-8 pb-4 text-center">
                    <div className="w-16 h-16 bg-slate-50 dark:bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-6">
                        {currentStep.icon}
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">{currentStep.title}</h2>
                    <p className="text-slate-500 dark:text-slate-400 text-sm">{currentStep.subtitle}</p>

                    <AnimatePresence mode="wait">
                        <motion.div
                            key={step}
                            initial={{ x: 20, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -20, opacity: 0 }}
                            className="mt-6"
                        >
                            {currentStep.content}
                        </motion.div>
                    </AnimatePresence>
                </div>

                <div className="p-8 pt-4">
                    <div className="flex gap-2 mb-6 justify-center">
                        {steps.map((_, i) => (
                            <div
                                key={i}
                                className={`h-1.5 rounded-full transition-all duration-300 ${i + 1 === step ? 'w-8 bg-brand-blue' : 'w-2 bg-slate-200 dark:bg-slate-700'}`}
                            />
                        ))}
                    </div>

                    {step < steps.length ? (
                        <Button
                            onClick={handleNext}
                            disabled={step === 1 && (!name || !role)}
                            className="w-full h-14 bg-brand-blue hover:bg-blue-600 text-white rounded-2xl text-lg font-bold shadow-lg shadow-blue-100 dark:shadow-blue-900/20 flex items-center justify-center gap-2"
                        >
                            Continue <ArrowRight size={20} />
                        </Button>
                    ) : (
                        <Button
                            onClick={handleFinish}
                            loading={isSaving}
                            className="w-full h-14 bg-brand-blue hover:bg-blue-600 text-white rounded-2xl text-lg font-bold shadow-lg shadow-blue-100 dark:shadow-blue-900/20"
                        >
                            Let's Go!
                        </Button>
                    )}
                </div>
            </motion.div>
        </div>
    );
}
