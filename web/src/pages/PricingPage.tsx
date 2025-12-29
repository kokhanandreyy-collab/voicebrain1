import { useState, useEffect } from 'react';
import { Check, X, Shield, HelpCircle } from 'lucide-react';
import api from '../api';
import { Button } from '../components/ui';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function PricingPage() {
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
    const [currency, setCurrency] = useState<'USD' | 'RUB'>('RUB');
    const [loading, setLoading] = useState<string | null>(null);
    const [prices, setPrices] = useState<any>(null); // { usd: {...}, rub: {...} }

    useEffect(() => {
        api.get('/payment/config')
            .then(res => {
                console.log("Pricing loaded:", res.data);
                setPrices(res.data);
            })
            .catch(err => console.error("Failed to load pricing", err));
    }, []);

    const getPrice = (tier: string, period: string, defaultVal: number | string) => {
        const currencyKey = currency.toLowerCase();
        if (!prices || !prices[currencyKey] || !prices[currencyKey][tier] || !prices[currencyKey][tier][period]) {
            return defaultVal;
        }
        return prices[currencyKey][tier][period];
    };

    const formatPrice = (amount: number | string) => {
        if (currency === 'RUB') {
            return `${amount} ₽`;
        }
        return `$${amount}`;
    };

    const handleSubscribe = async (tier: string) => {
        setLoading(tier);
        try {
            const { data } = await api.post('/payment/init', {
                tier,
                billing_period: billingCycle,
                currency
            });

            if (data.url) {
                window.location.href = data.url;
            }
        } catch (error) {
            console.error("Payment init failed", error);
            alert("Could not start payment flow");
        } finally {
            setLoading(null);
        }
    };

    // Features remain same
    const features = [
        {
            category: "Essentials (Available in All Plans)", rows: [
                { name: "Transcription per month", free: "120 mins", pro: "1200 mins", premium: "Unlimited" },
                { name: "Audio Storage", free: "3 months", pro: "1 year", premium: "Unlimited" },
                { name: "Global Search", free: true, pro: true, premium: true },
                { name: "Basic Export (txt)", free: true, pro: true, premium: true },
                { name: "Max File Size", free: "5 GB (8 hrs)", pro: "5 GB (8 hrs)", premium: "5 GB (8 hrs)" },
                { name: "Smart Summaries", free: "Basic", pro: "Advanced", premium: "Advanced" },
            ]
        },
        {
            category: "Power Features (Pro + Premium)", rows: [
                { name: "Unlimited Recording", free: false, pro: true, premium: true },
                { name: "Action Item Extraction", free: false, pro: true, premium: true },
                { name: "Speaker Diarization", free: false, pro: true, premium: true },
                { name: "Topic Clustering", free: false, pro: true, premium: true },
                { name: "Sentiment Analysis", free: false, pro: true, premium: true },
                { name: "Todoist Integration", free: false, pro: true, premium: true },
                { name: "Notion & Obsidian Sync", free: false, pro: true, premium: true },
            ]
        },
        {
            category: "Ultimate Scale (Premium Only)", rows: [
                { name: "Ask Your Brain (RAG)", free: false, pro: false, premium: true },
                { name: "Zapier / Webhooks", free: false, pro: false, premium: true },
                { name: "Priority Support", free: false, pro: false, premium: true },
                { name: "Early Access Features", free: false, pro: false, premium: true },
                { name: "White-label Sharing", free: false, pro: false, premium: true },
            ]
        }
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 selection:bg-brand-blue selection:text-white overflow-hidden relative">
            <Navbar />
            {/* Background Texture (Noise) */}
            <div className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none mix-blend-overlay"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
                }}
            />

            {/* Gradients */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-100/40 dark:bg-blue-900/10 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-100/40 dark:bg-purple-900/10 rounded-full blur-[120px]" />
            </div>

            <div className="max-w-7xl mx-auto space-y-12 py-20 px-4 sm:px-6 lg:px-8 relative z-10">

                {/* Header */}
                <div className="text-center space-y-6">
                    <h1 className="text-4xl md:text-5xl font-bold text-slate-900 dark:text-white tracking-tight">
                        Compare Plans
                    </h1>

                    <div className="flex flex-col items-center gap-4">
                        {/* Currency Toggle */}
                        <div className="bg-slate-200 dark:bg-slate-800 p-1 rounded-lg flex items-center">
                            <button
                                onClick={() => setCurrency('RUB')}
                                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-2 ${currency === 'RUB' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'}`}
                            >
                                🇷🇺 RUB
                            </button>
                            <button
                                onClick={() => setCurrency('USD')}
                                className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-2 ${currency === 'USD' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'}`}
                            >
                                🇺🇸 USD
                            </button>
                        </div>

                        {/* Billing Cycle Toggle */}
                        <div className="bg-slate-200 dark:bg-slate-800 p-1 rounded-xl flex items-center">
                            <button
                                onClick={() => setBillingCycle('monthly')}
                                className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${billingCycle === 'monthly' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'}`}
                            >
                                Monthly
                            </button>
                            <button
                                onClick={() => setBillingCycle('yearly')}
                                className={`px-6 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${billingCycle === 'yearly' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-300'}`}
                            >
                                Yearly <span className="text-[10px] bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-1.5 py-0.5 rounded-full uppercase tracking-wide">Save ~20%</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Comparison Table */}
                <div className="overflow-x-auto rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl dark:shadow-slate-950/50 bg-white dark:bg-slate-900">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr>
                                <th className="p-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 w-1/3 min-w-[200px]"></th>
                                <th className="p-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 w-1/5 min-w-[180px] text-center">
                                    <div className="text-xl font-bold text-slate-900 dark:text-white mb-2">Free</div>
                                    <div className="text-3xl font-bold text-slate-500 dark:text-slate-400">{formatPrice(0)}<span className="text-sm font-normal">/mo</span></div>
                                </th>
                                <th className="p-6 bg-slate-900 dark:bg-black border-b border-slate-900 dark:border-black w-1/5 min-w-[180px] text-center relative">
                                    <div className="absolute top-0 inset-x-0 bg-brand-blue h-1"></div>
                                    <div className="text-xl font-bold text-white mb-2">Pro</div>
                                    <div className="text-3xl font-bold text-white">
                                        {formatPrice(getPrice('pro', billingCycle, billingCycle === 'monthly' ? 490 : 332))}
                                        <span className="text-sm font-normal text-slate-400">/mo</span>
                                    </div>
                                    {billingCycle === 'yearly' && <div className="text-xs text-brand-blue font-bold mt-1">Billed {formatPrice(getPrice('pro', 'yearly', 3990))} yearly</div>}
                                </th>
                                <th className="p-6 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 w-1/5 min-w-[180px] text-center">
                                    <div className="text-xl font-bold text-slate-900 dark:text-white mb-2">Premium</div>
                                    <div className="text-3xl font-bold text-slate-900 dark:text-white">
                                        {formatPrice(getPrice('premium', billingCycle, billingCycle === 'monthly' ? 990 : 665))}
                                        <span className="text-sm font-normal text-slate-500 dark:text-slate-400">/mo</span>
                                    </div>
                                    {billingCycle === 'yearly' && <div className="text-xs text-slate-500 dark:text-slate-400 font-bold mt-1">Billed {formatPrice(getPrice('premium', 'yearly', 7990))} yearly</div>}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {features.map((section, sIdx) => (
                                <div key={sIdx} className="contents">
                                    {/* Category Header */}
                                    <tr>
                                        <td colSpan={4} className="p-4 bg-slate-50/50 dark:bg-slate-800/30 font-bold text-xs uppercase tracking-wider text-slate-400 dark:text-slate-500 border-y border-slate-100 dark:border-slate-800 pl-8">
                                            {section.category}
                                        </td>
                                    </tr>
                                    {/* Rows */}
                                    {section.rows.map((row: any, rIdx) => (
                                        <tr key={rIdx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors group">
                                            <td className="p-4 border-b border-slate-100 dark:border-slate-800 text-sm font-medium text-slate-700 dark:text-slate-300 pl-8 flex items-center gap-2">
                                                {row.name}
                                                <HelpCircle size={14} className="text-slate-300 dark:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity cursor-help" />
                                            </td>
                                            <td className="p-4 border-b border-slate-100 dark:border-slate-800 text-center text-sm text-slate-600 dark:text-slate-400">
                                                <FeatureValue value={row.free} />
                                            </td>
                                            <td className="p-4 border-b border-slate-100 dark:border-slate-800 text-center text-sm font-medium text-slate-900 dark:text-white bg-slate-50/30 dark:bg-slate-800/10">
                                                <FeatureValue value={row.pro} />
                                            </td>
                                            <td className="p-4 border-b border-slate-100 dark:border-slate-800 text-center text-sm text-slate-600 dark:text-slate-400">
                                                <FeatureValue value={row.premium} />
                                            </td>
                                        </tr>
                                    ))}
                                </div>
                            ))}

                            {/* Buttons Row */}
                            <tr>
                                <td className="p-6"></td>
                                <td className="p-6 text-center">
                                    <Button variant="outline" className="w-full" onClick={() => window.location.href = '/login?mode=signup'}>
                                        Start Free
                                    </Button>
                                </td>
                                <td className="p-6 text-center bg-slate-50/30 dark:bg-slate-800/10">
                                    <div className="space-y-4">
                                        <Button
                                            className="w-full bg-brand-blue hover:bg-blue-600 text-white"
                                            onClick={() => handleSubscribe('pro')}
                                            disabled={!!loading}
                                        >
                                            {loading === 'pro' ? 'Processing...' : 'Go Pro'}
                                        </Button>

                                        {currency === 'RUB' && (
                                            <div className="flex gap-2 justify-center opacity-60 grayscale hover:grayscale-0 transition-all">
                                                {/* Simple Placeholders for RU Payment Methods */}
                                                <div className="h-6 w-10 bg-slate-200 dark:bg-slate-700 rounded flex items-center justify-center text-[10px] font-bold text-slate-500">SBP</div>
                                                <div className="h-6 w-12 bg-slate-200 dark:bg-slate-700 rounded flex items-center justify-center text-[10px] font-bold text-slate-500">MIR</div>
                                            </div>
                                        )}
                                    </div>
                                </td>
                                <td className="p-6 text-center">
                                    <div className="space-y-4">
                                        <Button
                                            variant="outline"
                                            className="w-full border-slate-300 hover:border-slate-400"
                                            onClick={() => handleSubscribe('premium')}
                                            disabled={!!loading}
                                        >
                                            {loading === 'premium' ? 'Processing...' : 'Get Premium'}
                                        </Button>

                                        {currency === 'RUB' && (
                                            <div className="flex gap-2 justify-center opacity-60 grayscale hover:grayscale-0 transition-all">
                                                <div className="h-6 w-10 bg-slate-200 dark:bg-slate-700 rounded flex items-center justify-center text-[10px] font-bold text-slate-500">SBP</div>
                                                <div className="h-6 w-12 bg-slate-200 dark:bg-slate-700 rounded flex items-center justify-center text-[10px] font-bold text-slate-500">MIR</div>
                                            </div>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div className="text-center pt-8">
                    <p className="text-slate-400 text-sm flex items-center justify-center gap-2">
                        <Shield size={14} /> Secure payment • Cancel anytime • {currency === 'RUB' ? 'Russian Cards Accepted' : 'International Cards Accepted'}
                    </p>
                </div>
            </div>

            <Footer />
        </div>
    );
}

function FeatureValue({ value }: { value: string | boolean }) {
    if (value === true) {
        return <div className="flex justify-center"><div className="bg-green-100 text-green-600 p-1 rounded-full"><Check size={16} strokeWidth={3} /></div></div>;
    }
    if (value === false) {
        return <div className="flex justify-center"><div className="bg-red-50 text-red-300 p-1 rounded-full"><X size={16} strokeWidth={3} /></div></div>;
    }
    return <span>{value}</span>;
}
