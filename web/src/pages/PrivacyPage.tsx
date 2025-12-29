import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function PrivacyPage() {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-12">
            <div className="max-w-3xl mx-auto space-y-8">
                <Link to="/" className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-brand-blue dark:hover:text-blue-400 transition-colors">
                    <ArrowLeft size={20} /> Back to Home
                </Link>

                <article className="prose prose-slate dark:prose-invert lg:prose-xl">
                    <h1>Privacy Policy</h1>
                    <p className="text-sm text-slate-500">Last Updated: December 25, 2025</p>

                    <p>
                        At VoiceBrain ("we", "us", or "our"), we are committed to protecting your privacy. This Privacy Policy explains how our service collects, uses, and safeguards the information you provide.
                    </p>

                    <h2>1. Information We Collect</h2>
                    <ul>
                        <li><strong>Account Information:</strong> We collect your name, email address, and profile picture when you sign up using Google, Apple, or GitHub authentication methods.</li>
                        <li><strong>Audio Data:</strong> We collect and process the audio recordings you voluntarily upload to our service.</li>
                        <li><strong>Transcriptions & Metadata:</strong> We generate and store text transcriptions, summaries, tags, and action items derived from your audio data using AI processing.</li>
                        <li><strong>Usage Data:</strong> We collect anonymous metrics about how you interact with our application to improve performance and user experience.</li>
                    </ul>

                    <h2>2. How We Use Your Data</h2>
                    <p>
                        Your data is used primarily to provide the core functionality of VoiceBrain:
                    </p>
                    <ul>
                        <li>To transcribe and summarize your voice notes.</li>
                        <li>To organize and search your content.</li>
                        <li>To improve the accuracy of our AI models (only with your explicit consent or via generic feedback).</li>
                    </ul>

                    <h2>3. Third-Party Processors</h2>
                    <p>
                        We use trusted third-party providers to power our infrastructure:
                    </p>
                    <ul>
                        <li><strong>AI Processing:</strong> We may use OpenAI, Anthropic, or DeepSeek APIs to process your text and audio. Data sent to these providers is ephemeral and not used to train their global models (per our enterprise agreements).</li>
                        <li><strong>Storage:</strong> Your files are securely stored on AWS S3 or compatible cloud object storage.</li>
                        <li><strong>Authentication:</strong> We use industry-standard OAuth providers (Google, GitHub) for secure login.</li>
                    </ul>

                    <h2>4. Data Retention</h2>
                    <p>
                        We retain your data fo as long as your account is active. You may delete individual notes or your entire account at any time via the "Settings" page, which will permanently remove your data from our servers.
                    </p>

                    <h2>5. Contact Us</h2>
                    <p>
                        If you have questions about this policy, please contact us at support@voicebrain.ai.
                    </p>
                </article>
            </div>
        </div>
    );
}
