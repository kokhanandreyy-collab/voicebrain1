import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '../components/ui';

export default function VerifyPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');

    const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
    const [message, setMessage] = useState('Verifying your email...');

    useEffect(() => {
        if (!token) {
            setStatus('error');
            setMessage('No verification token found.');
            return;
        }

        const verify = async () => {
            try {
                await api.get(`/auth/verify?token=${token}`);
                setStatus('success');
                setMessage('Email verified successfully!');
            } catch (error: any) {
                setStatus('error');
                setMessage(error.response?.data?.detail || 'Verification failed. Token might be invalid or expired.');
            }
        };
        verify();
    }, [token]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
            <div className="bg-white dark:bg-slate-900 p-8 rounded-2xl shadow-xl max-w-md w-full text-center space-y-6">

                {status === 'verifying' && (
                    <div className="flex flex-col items-center gap-4">
                        <Loader2 className="w-12 h-12 text-brand-blue animate-spin" />
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white">Verifying...</h2>
                        <p className="text-slate-500 dark:text-slate-400">Please wait while we confirm your email.</p>
                    </div>
                )}

                {status === 'success' && (
                    <div className="flex flex-col items-center gap-4">
                        <CheckCircle2 className="w-16 h-16 text-green-500" />
                        <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Verified!</h2>
                        <p className="text-slate-500 dark:text-slate-400">{message}</p>
                        <Button onClick={() => navigate('/login')} className="w-full mt-4">
                            Go to Login
                        </Button>
                    </div>
                )}

                {status === 'error' && (
                    <div className="flex flex-col items-center gap-4">
                        <XCircle className="w-16 h-16 text-red-500" />
                        <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Verification Failed</h2>
                        <p className="text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-4 py-2 rounded-lg text-sm">{message}</p>
                        <Button variant="outline" onClick={() => navigate('/login')} className="w-full mt-4">
                            Back to Login
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
}
