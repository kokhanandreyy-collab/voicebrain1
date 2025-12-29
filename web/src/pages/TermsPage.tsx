import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function TermsPage() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-12">
            <div className="max-w-3xl mx-auto space-y-8">
                <Link to="/" className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-brand-blue dark:hover:text-blue-400 transition-colors">
                    <ArrowLeft size={20} /> Back to Home
                </Link>

                <article className="prose prose-slate dark:prose-invert lg:prose-xl">
                    <h1>Terms of Service</h1>
                    <p className="text-sm text-slate-500">Last Updated: December 25, 2025</p>

                    <p>
                        Welcome to VoiceBrain. By accessing or using our website and services, you agree to be bound by these Terms of Service.
                    </p>

                    <h2>1. Use of Service</h2>
                    <p>
                        VoiceBrain provides AI-powered voice note transcription and organization. You agree to use the service only for lawful purposes and in accordance with these Terms.
                    </p>

                    <h2>2. User Accounts</h2>
                    <p>
                        You are responsible for maintaining the confidentiality of your account credentials. You are responsible for all activities that occur under your account.
                    </p>

                    <h2>3. Intellectual Property</h2>
                    <p>
                        You retain full ownership of the audio content and transcriptions you create using VoiceBrain. We claim no intellectual property rights over the material you provide to the service.
                    </p>

                    <h2>4. Termination</h2>
                    <p>
                        We reserve the right to suspend or terminate your account at our sole discretion if we find that you have violated these Terms, especially regarding:
                    </p>
                    <ul>
                        <li>Interfering with the proper working of the Service.</li>
                        <li>Attempting to bypass security measures.</li>
                        <li>Using the service for illegal activities.</li>
                    </ul>

                    <h2>5. Disclaimer of Warranties</h2>
                    <p>
                        The service is provided "as is" and "as available" without any warranties of any kind. We do not guarantee that the service will be uninterrupted or error-free.
                    </p>

                    <h2>6. Limitation of Liability</h2>
                    <p>
                        In no event shall VoiceBrain be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or related to your use of the service.
                    </p>

                    <h2>7. Changes to Terms</h2>
                    <p>
                        We may modify these Terms at any time. We will provide notice of significant changes by posting an announcement on our website.
                    </p>
                </article>
            </div>
        </div>
    );
}
