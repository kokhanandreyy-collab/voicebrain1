import { Link } from 'react-router-dom';
import { useState } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import { Mic, CheckCircle2, Calendar, Share2, Shield, Zap, ArrowRight, Sparkles, BrainCircuit, FileText, Video, Search, Lock, Tag, Loader2 } from 'lucide-react';
import { Button } from '../components/ui';

import api from '../api';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function LandingPage() {
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');
    const [isLoadingPayment, setIsLoadingPayment] = useState<string | null>(null);

    const handleUpgrade = async (tier: string) => {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        setIsLoadingPayment(tier);
        try {
            const { data } = await api.post('/payment/init', {
                tier,
                billing_period: billingCycle
            });
            window.location.href = data.url;
        } catch (error) {
            console.error("Payment init failed", error);
            alert("Could not start payment. Please try again.");
            setIsLoadingPayment(null);
        }
    };
    const fadeInUp = {
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0, transition: { duration: 0.5 } }
    };



    const staggerContainer = {
        whileInView: {
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100 selection:bg-brand-blue selection:text-white overflow-x-hidden">
            {/* Background Texture (Noise) - The "Modern" Touch */}
            <div className="fixed inset-0 z-0 opacity-[0.03] pointer-events-none mix-blend-overlay"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
                }}
            />

            {/* Gradients */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-100/40 dark:bg-blue-900/20 rounded-full blur-[120px]" />
                <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-purple-100/40 dark:bg-purple-900/20 rounded-full blur-[120px]" />
            </div>

            {/* Navbar */}
            <Navbar />

            {/* Hero Section */}
            <section className="relative pt-28 pb-12 lg:pt-36 lg:pb-16 px-6 z-10 overflow-hidden min-h-[85vh] flex items-center">
                <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-10 lg:gap-12 items-stretch">
                    <div className="flex flex-col justify-center space-y-6 text-center lg:text-left py-4">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6 }}
                            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-brand-blue dark:text-blue-400 text-xs font-bold uppercase tracking-wider border border-blue-100 dark:border-blue-800 self-center lg:self-start"
                        >
                            <Sparkles size={12} />
                            VoiceBrain AI 2.0
                        </motion.div>

                        <motion.h1
                            className="text-4xl lg:text-6xl font-bold tracking-tight text-slate-900 dark:text-white leading-[1.1]"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1, duration: 0.6 }}
                        >
                            Voice Notes That Become Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-blue to-purple-600">Second Brain</span>
                        </motion.h1>

                        <motion.div
                            className="space-y-5"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2, duration: 0.6 }}
                        >
                            <h2 className="text-lg lg:text-xl text-slate-700 dark:text-slate-300 font-semibold tracking-tight">
                                Turn the chaos of daily speech into perfect structure.
                            </h2>
                            <p className="text-base lg:text-lg text-slate-500 dark:text-slate-400 leading-relaxed max-w-xl mx-auto lg:mx-0">
                                Ideas, shopping lists, meeting minutes—standard recorders just save audio. <span className="font-semibold text-slate-700 dark:text-slate-300">VoiceBrain understands you</span>.
                                It listens, transcribes, and transforms streams of consciousness into clear, actionable, personalized notes.
                            </p>
                            <p className="text-xl text-slate-600 dark:text-slate-400 mt-4">The voice recorder that actually understands you — used daily by founders, creators, and deep thinkers.</p>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 max-w-4xl mx-auto lg:mx-0">
                                <div className="text-center lg:text-left">
                                    <div className="text-3xl font-bold text-brand-blue dark:text-blue-400">1200+</div>
                                    <p className="text-slate-600 dark:text-slate-400 mt-1 text-sm font-medium">minutes transcription in Pro</p>
                                </div>
                                <div className="text-center lg:text-left">
                                    <div className="text-3xl font-bold text-brand-blue dark:text-blue-400">20+</div>
                                    <p className="text-slate-600 dark:text-slate-400 mt-1 text-sm font-medium">direct app integrations</p>
                                </div>
                                <div className="text-center lg:text-left">
                                    <div className="text-3xl font-bold text-brand-blue dark:text-blue-400">Neural</div>
                                    <p className="text-slate-600 dark:text-slate-400 mt-1 text-sm font-medium">semantic search engine</p>
                                </div>
                            </div>
                        </motion.div>

                        <motion.div
                            className="flex flex-col sm:flex-row items-center lg:justify-start justify-center gap-3 pt-2"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3, duration: 0.6 }}
                        >
                            <Link to="/login" className="w-full sm:w-auto">
                                <Button size="lg" className="w-full sm:w-auto h-14 px-8 text-base rounded-full bg-slate-900 dark:bg-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100 shadow-xl shadow-slate-900/20 dark:shadow-none text-white">
                                    Start for Free <ArrowRight size={18} className="ml-2" />
                                </Button>
                            </Link>
                            <p className="text-xs text-slate-400 font-medium whitespace-nowrap">No Credit Card • Full Access Trial</p>
                        </motion.div>


                    </div>

                    <div className="relative flex items-center justify-center lg:h-auto h-[400px]">
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[100%] h-[100%] bg-blue-200/30 rounded-full blur-3xl -z-10" />
                        <img
                            src="/hero.png"
                            alt="VoiceBrain Mobile App Interface"
                            className="w-full max-w-[450px] lg:max-w-full h-auto object-contain drop-shadow-2xl"
                        />
                    </div>
                </div>
            </section>

            {/* Transformation Section - The "Magical" Demo */}
            <section className="py-20 bg-white dark:bg-slate-950 relative z-10 border-b border-slate-100 dark:border-slate-800">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">Standard AI vs <span className="text-brand-blue">VoiceBrain</span></h2>
                        <p className="text-lg text-slate-500 max-w-2xl mx-auto">See the difference. We don't just transcribe words; we extract value.</p>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
                        {/* LEFT: messy raw */}
                        <div className="bg-slate-50 rounded-2xl p-8 border border-slate-200/60 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 bg-red-100 text-red-600 px-3 py-1 rounded-bl-xl text-xs font-bold uppercase">Others</div>
                            <h3 className="font-bold text-slate-900 text-xl mb-4 flex items-center gap-2"><Mic size={20} className="text-slate-400" /> Raw Transcription</h3>
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 opacity-50">
                                    <div className="h-8 flex-1 bg-slate-200 rounded-lg animate-pulse"></div>
                                    <div className="h-8 w-12 bg-slate-200 rounded-lg animate-pulse"></div>
                                </div>
                                <p className="text-slate-500 text-sm leading-relaxed p-4 bg-white rounded-xl border border-slate-100 font-mono">
                                    "Um, so yeah, remind me to call John about the... uh, what was it... the Q3 projections. Also we need milk. And oh, send the slide deck to Sarah by Friday. Actually make it Thursday. Wait, did I say milk? Yeah, get almond milk."
                                </p>
                                <div className="text-xs text-red-400 font-medium mt-2 flex items-center gap-1">
                                    <div className="w-2 h-2 rounded-full bg-red-400"></div> No Structure
                                    <div className="w-2 h-2 rounded-full bg-red-400 ml-2"></div> No Action Items
                                </div>
                            </div>
                        </div>

                        {/* RIGHT: Structured VoiceBrain */}
                        <div className="bg-gradient-to-br from-white to-blue-50/50 rounded-2xl p-8 border border-brand-blue/20 relative shadow-xl shadow-brand-blue/5 overflow-hidden">
                            <div className="absolute top-0 right-0 bg-brand-blue text-white px-3 py-1 rounded-bl-xl text-xs font-bold uppercase flex items-center gap-1"><Sparkles size={10} /> VoiceBrain</div>
                            <h3 className="font-bold text-slate-900 text-xl mb-4 flex items-center gap-2"><BrainCircuit size={20} className="text-brand-blue" /> Intelligent Note</h3>

                            <div className="space-y-3">
                                {/* Title */}
                                <div className="p-3 bg-white rounded-lg border border-slate-100 shadow-sm">
                                    <div className="text-xs font-bold text-slate-400 uppercase mb-1">Summary</div>
                                    <h4 className="font-bold text-slate-900">Team Sync & Errands</h4>
                                </div>

                                {/* Tasks */}
                                <div className="p-3 bg-white rounded-lg border border-slate-100 shadow-sm">
                                    <div className="text-xs font-bold text-slate-400 uppercase mb-2">Action Items (Todoist Integration)</div>
                                    <div className="space-y-2">
                                        <div className="flex items-start gap-2 text-sm text-slate-700">
                                            <div className="mt-0.5 w-4 h-4 rounded border border-slate-300 flex items-center justify-center text-brand-blue"><CheckCircle2 size={12} /></div>
                                            <span>Call John re: Q3 Projections</span>
                                        </div>
                                        <div className="flex items-start gap-2 text-sm text-slate-700">
                                            <div className="mt-0.5 w-4 h-4 rounded border border-slate-300 flex items-center justify-center text-brand-blue"><CheckCircle2 size={12} /></div>
                                            <span>Send deck to Sarah <span className="text-red-500 bg-red-50 px-1 rounded text-[10px] font-bold">Thu Deadline</span></span>
                                        </div>
                                    </div>
                                </div>

                                {/* List */}
                                <div className="p-3 bg-white rounded-lg border border-slate-100 shadow-sm flex items-center justify-between">
                                    <div>
                                        <div className="text-xs font-bold text-slate-400 uppercase mb-1">Shopping List</div>
                                        <div className="text-sm font-medium text-slate-800">• Almond Milk</div>
                                    </div>
                                    <div className="bg-green-50 text-green-700 p-2 rounded-lg">
                                        <Tag size={16} />
                                    </div>
                                </div>

                                <div className="flex gap-2 justify-center mt-2 opacity-80 pt-2 border-t border-slate-100/50">
                                    <span className="text-[10px] uppercase font-bold bg-red-50 text-red-600 px-2 py-0.5 rounded-full border border-red-100 flex items-center gap-1">Todoist</span>
                                    <span className="text-[10px] uppercase font-bold bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full border border-purple-100 flex items-center gap-1">Obsidian</span>
                                    <span className="text-[10px] uppercase font-bold bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full border border-blue-100 flex items-center gap-1">Notion</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Personalization Section */}
            <section className="py-16 bg-slate-50 border-t border-slate-100 overflow-hidden relative z-10">
                <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
                    {/* Visual UI Layout for Personalization - Left Side */}
                    <div className="relative order-2 lg:order-1 flex flex-col justify-center">
                        <div className="relative z-10 w-full max-w-md mx-auto lg:mx-0 scale-90 lg:scale-100 origin-center lg:origin-left">
                            {/* Card 1: Early Stage */}
                            <motion.div
                                className="bg-white p-5 rounded-xl border border-slate-100 shadow-sm opacity-60 scale-95 origin-top-left ml-12 mb-[-50px] z-10"
                                initial={{ y: 20, opacity: 0 }}
                                whileInView={{ y: 0, opacity: 0.6 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 }}
                            >
                                <span className="text-[10px] font-bold text-slate-400 mb-1 block uppercase tracking-wider">1 Week Ago</span>
                                <h4 className="font-bold text-slate-800 text-sm mb-1 tracking-tight">Marketing Ideas</h4>
                                <p className="text-xs text-slate-500">Need to run ads on socials. Check budget.</p>
                            </motion.div>

                            {/* Card 2: Mid Stage */}
                            <motion.div
                                className="bg-white p-5 rounded-xl border border-slate-200 shadow-md opacity-80 scale-98 origin-top-left ml-6 mb-[-50px] relative z-20"
                                initial={{ y: 30, opacity: 0 }}
                                whileInView={{ y: 0, opacity: 0.8 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.2 }}
                            >
                                <span className="text-[10px] font-bold text-slate-400 mb-1 block uppercase tracking-wider">Yesterday</span>
                                <div className="flex gap-2 mb-1">
                                    <span className="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded text-[10px] font-medium">#work</span>
                                    <span className="bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded text-[10px] font-medium">#ideas</span>
                                </div>
                                <h4 className="font-bold text-slate-800 text-sm mb-1 tracking-tight">Marketing Plan Q4</h4>
                                <p className="text-xs text-slate-600">Launch ads on Friday. Budget approved.</p>
                            </motion.div>

                            {/* Card 3: Advanced Personalized */}
                            <motion.div
                                className="bg-white p-6 rounded-xl border border-brand-blue shadow-xl relative z-30 ring-1 ring-brand-blue/10"
                                initial={{ y: 40, opacity: 0 }}
                                whileInView={{ y: 0, opacity: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.3 }}
                            >
                                <span className="text-[10px] font-bold text-brand-blue mb-2 flex items-center gap-1 uppercase tracking-wider"><Sparkles size={10} /> Today</span>
                                <div className="flex gap-2 mb-3">
                                    <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-[10px] font-bold">🚀 Promo</span>
                                    <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-[10px] font-bold">🔥 ASAP</span>
                                </div>
                                <h4 className="font-bold text-lg text-slate-900 mb-2 tracking-tight">Launch Strategy 🎯</h4>
                                <div className="space-y-2 text-xs">
                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 border border-slate-100">
                                        <div className="w-4 h-4 rounded border-2 border-slate-300 flex items-center justify-center bg-white"></div>
                                        <span className="text-slate-700 font-medium">Prepare creatives for review</span>
                                    </div>
                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 border border-slate-100">
                                        <div className="w-4 h-4 rounded border-2 border-slate-300 flex items-center justify-center bg-white"></div>
                                        <span className="text-slate-700 font-medium">Sync with <span className="text-brand-blue font-bold">@design</span> team</span>
                                    </div>
                                </div>
                            </motion.div>
                        </div>
                    </div>

                    <div className="space-y-6 order-1 lg:order-2 flex flex-col justify-center">
                        <div className="mb-2">
                            <h2 className="text-3xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight tracking-tight">AI That <br /><span className="text-brand-blue">Learns Your Mind</span></h2>
                            <p className="text-base text-slate-500 leading-relaxed">VoiceBrain doesn't just transcribe—it learns from you. It recognizes your unique vocabulary, sentence structure, and priorities.</p>
                        </div>

                        <div className="grid sm:grid-cols-2 gap-4">
                            {[
                                { title: "Voice & Style", desc: "Understands your accent, speed, and emotional tone." },
                                { title: "Topics & Priorities", desc: "Highlights what matters most to you automatically." },
                                { title: "Smart Tags", desc: "Auto-tags notes based on your personal taxonomy." },
                                { title: "Custom Formats", desc: "Outputs text exactly how you like to read it." }
                            ].map((item, i) => (
                                <div key={i} className="bg-slate-50/50 p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors group">
                                    <div className="w-1.5 h-1.5 rounded-full bg-brand-blue mb-2 group-hover:scale-125 transition-transform" />
                                    <h4 className="font-bold text-slate-900 text-sm mb-1 tracking-tight">{item.title}</h4>
                                    <p className="text-slate-500 text-xs leading-relaxed">{item.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* Search Section */}
            <section className="py-16 bg-white border-y border-slate-200 relative overflow-hidden">
                <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
                    <div className="space-y-6 h-full flex flex-col justify-center">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 leading-tight tracking-tight">Instant Cognitive <br /> <span className="text-purple-600">Retrieval</span></h2>
                        <p className="text-base lg:text-lg text-slate-600 leading-relaxed">
                            Forget keyword guessing. VoiceBrain's neural engine maps the semantic relationships between your thoughts.
                            Ask natural questions like <em>"What did I decide about the Q3 budget?"</em> and instantly retrieve the exact context, decision, and related notes—even if you never used those exact words.
                        </p>
                        <div className="flex gap-4 pt-2">
                            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
                                <BrainCircuit size={16} className="text-brand-blue" /> Neural Mapping
                            </div>
                            <div className="flex items-center gap-2 text-sm font-bold text-slate-700 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
                                <Search size={16} className="text-purple-600" /> Context Aware
                            </div>
                        </div>
                    </div>

                    <div className="relative h-full flex items-center justify-center p-4">
                        <div className="absolute inset-0 bg-purple-100/50 rounded-full blur-3xl scale-75 -z-10" />
                        <img
                            src="/search.png"
                            alt="Semantic Search Neural Network Visualization"
                            className="w-full h-auto rounded-lg shadow-xl border border-white/50 bg-white/20 backdrop-blur-sm"
                        />
                    </div>
                </div>
            </section>

            {/* Process Section */}
            <section className="py-20 bg-slate-900 text-white z-10 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-900 to-blue-900/20" />

                <div className="max-w-7xl mx-auto px-6 relative z-10">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight">From Thought to Action</h2>
                        <p className="text-slate-400 text-lg max-w-2xl mx-auto">Three simple steps to unmuddle your mind.</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-10 text-center relative">
                        <div className="hidden md:block absolute top-10 left-[15%] right-[15%] h-px bg-slate-800 -z-10" />

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            className="space-y-4"
                        >
                            <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto shadow-xl">
                                <Mic size={32} className="text-red-500" />
                            </div>
                            <h3 className="text-xl font-bold text-white tracking-tight">1. Record</h3>
                            <p className="text-slate-400 text-sm max-w-[200px] mx-auto">
                                One tap. Speak freely. <br /> No structure needed.
                            </p>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.2 }}
                            className="space-y-4"
                        >
                            <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto shadow-xl">
                                <BrainCircuit size={32} className="text-brand-blue" />
                            </div>
                            <h3 className="text-xl font-bold text-white tracking-tight">2. Process</h3>
                            <p className="text-slate-400 text-sm max-w-[200px] mx-auto">
                                AI structures, tags, and <br /> summarizes instantly.
                            </p>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.4 }}
                            className="space-y-4"
                        >
                            <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto shadow-xl">
                                <div className="grid grid-cols-2 gap-1.5 text-white">
                                    <FileText size={14} />
                                    <Calendar size={14} />
                                    <Share2 size={14} />
                                    <Tag size={14} />
                                </div>
                            </div>
                            <h3 className="text-xl font-bold text-white tracking-tight">3. Action</h3>
                            <p className="text-slate-400 text-sm max-w-[200px] mx-auto">
                                Export to your tools or <br /> share with your team.
                            </p>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* POWER FEATURES GRID (The User Requested List) */}
            <section className="py-20 bg-slate-900 text-white relative z-10">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                            className="inline-block px-3 py-1 rounded-full bg-slate-800 text-brand-blue border border-slate-700 text-xs font-bold uppercase tracking-wider mb-4"
                        >
                            Unlock Potential
                        </motion.div>
                        <h2 className="text-3xl md:text-5xl font-bold mb-6 tracking-tight">Everything You Need <br /> To Scale Your Mind</h2>
                        <p className="text-lg text-slate-400 max-w-2xl mx-auto">Powerful tools built for high-performance individuals.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {/* 1. Ask AI (RAG) */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-brand-blue/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4 text-blue-400 group-hover:scale-110 transition-transform"><BrainCircuit size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Ask Your Brain (RAG)</h3>
                            <p className="text-slate-400 text-sm">Chat with your notes. Ask "What was the idea for X?" and get an instant answer synthesized from your history.</p>
                        </div>

                        {/* 2. Integrations */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-red-500/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center mb-4 text-red-400 group-hover:scale-110 transition-transform"><Share2 size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Export to 20+ Apps</h3>
                            <p className="text-slate-400 text-sm">
                                Direct sync with <strong>Obsidian</strong>, <strong>Notion</strong>, <strong>Reflect</strong>, <strong>Craft</strong>, <strong>Apple Notes</strong>, <strong>Todoist</strong>, <strong>TickTick</strong>, <strong>Microsoft To Do</strong>, <strong>Readwise</strong>, <strong>Evernote</strong> and more.
                            </p>
                        </div>

                        {/* 3. Editor */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-purple-500/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center mb-4 text-purple-400 group-hover:scale-110 transition-transform"><FileText size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Powerful Editor</h3>
                            <p className="text-slate-400 text-sm">Full Markdown support. Edit generated notes, add headers, bold, and lists effortlessly.</p>
                        </div>

                        {/* 4. Custom Output Styles */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-yellow-500/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center mb-4 text-yellow-400 group-hover:scale-110 transition-transform"><Sparkles size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Custom Output Styles</h3>
                            <p className="text-slate-400 text-sm">Teach AI your format. Want "Bullet Journal" or "Executive Brief"? Just save your prompt preference.</p>
                        </div>

                        {/* 5. Topic Clustering */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-green-500/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center mb-4 text-green-400 group-hover:scale-110 transition-transform"><Zap size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Topic Clustering</h3>
                            <p className="text-slate-400 text-sm">Auto-groups related notes. "You spoke about Project X 5 times." Spot trends in your own thinking.</p>
                        </div>

                        {/* 6. Speaker Diarization */}
                        <div className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700 hover:border-pink-500/50 transition-colors group">
                            <div className="w-10 h-10 rounded-lg bg-pink-500/10 flex items-center justify-center mb-4 text-pink-400 group-hover:scale-110 transition-transform"><Mic size={24} /></div>
                            <h3 className="text-lg font-bold mb-2">Speaker Identification</h3>
                            <p className="text-slate-400 text-sm">Perfect for meetings. Automatically detects and labels different speakers in your recordings.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Use Cases Section */}
            <section className="py-20 bg-slate-50 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Who is VoiceBrain for?</h2>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 text-center shadow-sm">
                            <div className="w-12 h-12 bg-blue-50 text-brand-blue rounded-full flex items-center justify-center mx-auto mb-4"><Zap size={20} /></div>
                            <h4 className="font-bold text-lg mb-2">Founders</h4>
                            <p className="text-slate-500 text-sm">Capture pitch ideas, strategy shifts, and team tasks while walking or commuting.</p>
                        </div>
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 text-center shadow-sm">
                            <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center mx-auto mb-4"><Video size={20} /></div>
                            <h4 className="font-bold text-lg mb-2">Content Creators</h4>
                            <p className="text-slate-500 text-sm">Draft newsletters, YouTube scripts, and blog posts by just talking out loud.</p>
                        </div>
                        <div className="bg-white p-6 rounded-2xl border border-slate-200 text-center shadow-sm">
                            <div className="w-12 h-12 bg-green-50 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4"><CheckCircle2 size={20} /></div>
                            <h4 className="font-bold text-lg mb-2">Product Managers</h4>
                            <p className="text-slate-500 text-sm"> Summarize meetings instantly. Turn stakeholder feedback into actionable tickets automatically.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* What you get today / Security */}
            <section className="py-20 px-6 relative bg-white z-10 border-t border-slate-100">
                <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
                    <motion.div
                        initial="initial"
                        whileInView="whileInView"
                        viewport={{ once: true }}
                        variants={staggerContainer}
                    >
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-8 leading-tight tracking-tight">Enterprise-Grade <br /> Security & Speed</h2>
                        <div className="space-y-4">
                            <motion.div variants={fadeInUp} viewport={{ once: true }} className="flex gap-4 bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                                <div className="w-10 h-10 rounded-lg bg-green-50 border border-green-100 flex items-center justify-center shrink-0">
                                    <Shield size={20} className="text-green-600" />
                                </div>
                                <div>
                                    <h4 className="font-bold text-slate-900 text-base mb-1">SOC2 Compliant</h4>
                                    <p className="text-sm text-slate-500">Your data is encrypted at rest and in transit. We prioritize your privacy above all else.</p>
                                </div>
                            </motion.div>
                            <motion.div variants={fadeInUp} viewport={{ once: true }} className="flex gap-4 bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                                <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                                    <Zap size={20} className="text-blue-600" />
                                </div>
                                <div>
                                    <h4 className="font-bold text-slate-900 text-base mb-1">Lightning Fast</h4>
                                    <p className="text-sm text-slate-500">Optimized for speed. Zero loading times. Instant sync across all your devices.</p>
                                </div>
                            </motion.div>
                            <motion.div variants={fadeInUp} viewport={{ once: true }} className="flex gap-4 bg-white p-5 rounded-xl shadow-sm border border-slate-100">
                                <div className="w-10 h-10 rounded-lg bg-purple-50 border border-purple-100 flex items-center justify-center shrink-0">
                                    <Lock size={20} className="text-purple-600" />
                                </div>
                                <div>
                                    <h4 className="font-bold text-slate-900 text-base mb-1">Private by Default</h4>
                                    <p className="text-sm text-slate-500">We don't sell your data. We don't train public models on your private notes.</p>
                                </div>
                            </motion.div>
                        </div>
                    </motion.div>

                    <div className="relative h-full flex items-center justify-center">
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[100%] h-[100%] bg-green-50/50 rounded-full blur-[80px] -z-10" />
                        <img
                            src="/security.png"
                            alt="Enterprise Security Shield"
                            className="w-full max-w-[400px] h-auto object-contain drop-shadow-xl"
                        />
                    </div>
                </div>
            </section>

            {/* Pricing Section */}
            <section className="py-20 bg-white relative z-10 border-t border-slate-100" id="pricing">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">Simple, Transparent Pricing</h2>
                        <p className="text-lg text-slate-500 max-w-xl mx-auto mb-8">Start for free, upgrade as you grow.</p>

                        {/* Billing Toggle */}
                        <div className="flex items-center justify-center gap-4">
                            <span className={clsx("text-sm font-bold transition-colors", billingCycle === 'monthly' ? "text-slate-900" : "text-slate-400")}>Monthly</span>
                            <button
                                onClick={() => setBillingCycle(prev => prev === 'monthly' ? 'yearly' : 'monthly')}
                                className="w-14 h-8 bg-slate-200 rounded-full p-1 relative transition-colors focus:outline-none focus:ring-2 focus:ring-brand-blue/50"
                            >
                                <motion.div
                                    className="w-6 h-6 bg-white rounded-full shadow-sm"
                                    animate={{ x: billingCycle === 'monthly' ? 0 : 24 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                />
                            </button>
                            <span className={clsx("text-sm font-bold transition-colors flex items-center gap-2", billingCycle === 'yearly' ? "text-slate-900" : "text-slate-400")}>
                                Yearly <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold">SAVE ~20%</span>
                            </span>
                        </div>
                    </div>

                    <div className="grid lg:grid-cols-3 gap-8 items-stretch">
                        {/* FREE TIER */}
                        <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-md transition-all relative flex flex-col">
                            <h3 className="font-bold text-2xl text-slate-900 mb-2">Free</h3>
                            <p className="text-slate-500 text-sm mb-6">For curious minds just starting out.</p>
                            <div className="mb-6">
                                <div className="flex items-baseline gap-1">
                                    <span className="text-4xl font-bold text-slate-900">$0</span>
                                    <span className="text-slate-500 font-medium">/mo</span>
                                </div>
                                <div className="text-xs text-transparent select-none mt-1">placeholder</div>
                            </div>
                            <Link to="/login?mode=signup" className="mb-8 block">
                                <button className="w-full py-3 rounded-xl bg-white border border-slate-300 text-slate-700 font-bold hover:bg-slate-50 transition-colors shadow-sm hover:scale-105 transform duration-200">
                                    Start Free
                                </button>
                            </Link>
                            <div className="space-y-4 mt-auto">
                                <div className="flex items-start gap-3 text-sm text-slate-600">
                                    <CheckCircle2 size={18} className="text-slate-400 shrink-0 mt-0.5" />
                                    <span><strong>120 minutes</strong> transcription monthly</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-600">
                                    <CheckCircle2 size={18} className="text-slate-400 shrink-0 mt-0.5" />
                                    <span>Unlimited notes & semantic search</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-600">
                                    <CheckCircle2 size={18} className="text-slate-400 shrink-0 mt-0.5" />
                                    <span>AI summary, tags & action items</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-600">
                                    <CheckCircle2 size={18} className="text-slate-400 shrink-0 mt-0.5" />
                                    <span>Export via Copy, Email, Markdown</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-600">
                                    <CheckCircle2 size={18} className="text-slate-400 shrink-0 mt-0.5" />
                                    <span>3-month history retention</span>
                                </div>
                            </div>
                        </div>

                        {/* PRO TIER */}
                        <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-3xl p-8 border border-blue-200 shadow-xl relative flex flex-col transform lg:-translate-y-4 z-10">
                            <div className="absolute top-0 right-0 bg-brand-blue text-white text-xs font-bold px-3 py-1.5 rounded-bl-xl rounded-tr-2xl">MOST POPULAR</div>

                            <h3 className="font-bold text-2xl text-slate-900 mb-2">Pro</h3>
                            <p className="text-slate-600 text-sm mb-6">For power users building knowledge.</p>
                            <div className="mb-6">
                                <div className="flex items-baseline gap-1">
                                    <span className="text-4xl font-bold text-slate-900">{billingCycle === 'monthly' ? '$9.99' : '$8'}</span>
                                    <span className="text-slate-500 font-medium">/mo</span>
                                </div>
                                <div className="text-xs text-slate-500 font-medium mt-1">
                                    {billingCycle === 'yearly' ? 'Billed $96 yearly' : 'Billed monthly'}
                                </div>
                            </div>

                            <button
                                onClick={() => handleUpgrade('pro')}
                                disabled={!!isLoadingPayment}
                                className="w-full py-3 rounded-xl bg-brand-blue text-white font-bold hover:bg-blue-600 transition-colors shadow-lg shadow-blue-500/30 mb-8 flex items-center justify-center gap-2 hover:scale-105 transform duration-200"
                            >
                                {isLoadingPayment === 'pro' && <Loader2 size={18} className="animate-spin" />}
                                Go Pro
                            </button>

                            <p className="text-xs text-brand-blue font-bold uppercase tracking-wider mb-4">Best for most users</p>
                            <div className="space-y-4 mt-auto">
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-brand-blue shrink-0 mt-0.5" />
                                    <span><strong>1200 minutes</strong> transcription monthly</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-brand-blue shrink-0 mt-0.5" />
                                    <span><strong>All direct integrations</strong> (Obsidian, Notion, Todoist, Apple Notes...)</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-brand-blue shrink-0 mt-0.5" />
                                    <span>Speaker diarization & topic clustering</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-brand-blue shrink-0 mt-0.5" />
                                    <span>1-year history retention</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-brand-blue shrink-0 mt-0.5" />
                                    <span>Priority email support</span>
                                </div>
                            </div>
                        </div>

                        {/* PREMIUM TIER */}
                        <div className="bg-gradient-to-br from-purple-50 to-fuchsia-100 rounded-3xl p-8 border border-purple-200 shadow-sm hover:shadow-md transition-all relative flex flex-col">
                            <h3 className="font-bold text-2xl text-slate-900 mb-2">Premium</h3>
                            <p className="text-slate-600 text-sm mb-6">For ultimate scale & insights.</p>
                            <div className="mb-6">
                                <div className="flex items-baseline gap-1">
                                    <span className="text-4xl font-bold text-slate-900">{billingCycle === 'monthly' ? '$19' : '$16'}</span>
                                    <span className="text-slate-500 font-medium">/mo</span>
                                </div>
                                <div className="text-xs text-slate-500 font-medium mt-1">
                                    {billingCycle === 'yearly' ? 'Billed $192 yearly' : 'Billed monthly'}
                                </div>
                            </div>
                            <button
                                onClick={() => handleUpgrade('premium')}
                                disabled={!!isLoadingPayment}
                                className="w-full py-3 rounded-xl bg-white border border-purple-300 text-purple-700 font-bold hover:bg-purple-50 transition-colors mb-8 shadow-sm flex items-center justify-center gap-2 hover:scale-105 transform duration-200"
                            >
                                {isLoadingPayment === 'premium' && <Loader2 size={18} className="animate-spin" />}
                                Get Premium
                            </button>
                            <p className="text-xs text-purple-600 font-bold uppercase tracking-wider mb-4">For power thinkers</p>
                            <div className="space-y-4 mt-auto">
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-purple-600 shrink-0 mt-0.5" />
                                    <span><strong>Unlimited</strong> transcription & history</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-purple-600 shrink-0 mt-0.5" />
                                    <span>Priority AI processing (faster)</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-purple-600 shrink-0 mt-0.5" />
                                    <span>Custom AI styles & advanced prompts</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-purple-600 shrink-0 mt-0.5" />
                                    <span>Early access to new features</span>
                                </div>
                                <div className="flex items-start gap-3 text-sm text-slate-700">
                                    <CheckCircle2 size={18} className="text-purple-600 shrink-0 mt-0.5" />
                                    <span>Premium chat support</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Integrations Marquee - Otter.ai Style */}
            <section className="py-16 bg-white dark:bg-slate-900 border-y border-slate-100 dark:border-slate-800 overflow-hidden relative">
                <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-white dark:from-slate-900 to-transparent z-10" />
                <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-white dark:from-slate-900 to-transparent z-10" />

                <div className="text-center mb-10">
                    <p className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">20+ DIRECT INTEGRATIONS • 8000+ VIA ZAPIER</p>
                </div>

                <div className="flex flex-col gap-8">
                    {/* Row 1 */}
                    <Marquee direction="left" speed={60}>
                        <IntegrationCard name="Todoist" desc="Turn your spoken thoughts into actionable tasks instantly." icon={<img src="https://cdn.simpleicons.org/todoist/E44332" className="w-7 h-7" alt="Todoist" />} />
                        <IntegrationCard name="Notion" desc="Sync meeting notes and action items to your databases." icon={<img src="https://cdn.simpleicons.org/notion/000000" className="w-7 h-7" alt="Notion" />} />
                        <IntegrationCard name="Obsidian" desc="Export thoughts as Markdown files to your second brain." icon={<img src="https://cdn.simpleicons.org/obsidian/483699" className="w-7 h-7" alt="Obsidian" />} />
                        <IntegrationCard name="Apple Notes" desc="Send formatted notes directly to your iCloud account." icon={<img src="https://cdn.simpleicons.org/apple/999999" className="w-7 h-7" alt="Apple Notes" />} />
                        <IntegrationCard name="Google Calendar" desc="Automatically detect dates and schedule events." icon={<img src="https://cdn.simpleicons.org/googlecalendar/4285F4" className="w-7 h-7" alt="Google Calendar" />} />
                        <IntegrationCard name="Microsoft To Do" desc="Seamlessly create tasks in your Microsoft ecosystem." icon={<img src="https://cdn.simpleicons.org/microsoft/00A4EF" className="w-7 h-7" alt="Microsoft" />} />
                    </Marquee>

                    {/* Row 2 */}
                    <Marquee direction="right" speed={60}>
                        <IntegrationCard name="Reflect" desc="Push notes to your mirrored daily notes in Reflect." icon={<Sparkles size={28} className="text-indigo-500" />} />
                        <IntegrationCard name="Craft" desc="Create beautiful documents from your voice memos." icon={<FileText size={28} className="text-purple-500" />} />
                        <IntegrationCard name="Readwise" desc="Save highlights to your Reader account automatically." icon={<img src="https://cdn.simpleicons.org/readwise/111111" className="w-7 h-7" alt="Readwise" />} />
                        <IntegrationCard name="Evernote" desc="Capture ideas and save them to notebooks." icon={<img src="https://cdn.simpleicons.org/evernote/00A82D" className="w-7 h-7" alt="Evernote" />} />
                        <IntegrationCard name="TickTick" desc="Quick add tasks with voice recognition." icon={<img src="https://cdn.simpleicons.org/ticktick/3273F5" className="w-7 h-7" alt="TickTick" />} />
                        <IntegrationCard name="Zapier" desc="Connect to 5000+ apps for unlimited automation." icon={<img src="https://cdn.simpleicons.org/zapier/FF4F00" className="w-7 h-7" alt="Zapier" />} />
                    </Marquee>
                </div>
            </section>

            {/* CTA */}
            <section className="py-24 px-6 text-center z-10 relative bg-brand-blue/5 dark:bg-brand-blue/10">
                <motion.div
                    className="max-w-3xl mx-auto space-y-8"
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                >
                    <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 dark:text-white leading-tight">Ready for notes that know you better than any other tool?</h2>
                    <p className="text-xl text-slate-600 dark:text-slate-400">
                        The only tool that turns spoken chaos into structured clarity — automatically.
                    </p>
                    <Link to="/login" className="inline-block">
                        <Button size="lg" className="h-16 px-12 text-xl rounded-full bg-slate-900 dark:bg-white hover:bg-slate-800 dark:hover:bg-slate-100 text-white dark:text-slate-900 shadow-2xl shadow-slate-900/30 dark:shadow-white/10">
                            Join VoiceBrain
                        </Button>
                    </Link>
                </motion.div>
            </section>

            <Footer />
        </div>
    );
}

function Marquee({ children, direction = 'left', speed = 20 }: { children: React.ReactNode, direction?: 'left' | 'right', speed?: number }) {
    return (
        <div className="flex overflow-hidden">
            <motion.div
                className="flex gap-6 shrink-0"
                initial={{ x: direction === 'left' ? 0 : '-50%' }}
                animate={{ x: direction === 'left' ? '-50%' : 0 }}
                transition={{
                    duration: speed,
                    ease: "linear",
                    repeat: Infinity
                }}
            >
                {children}
                {children}
            </motion.div>
        </div>
    );
}

function IntegrationCard({ name, desc, icon }: { name: string, desc: string, icon: React.ReactNode }) {
    return (
        <div className="flex items-start gap-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 w-[24rem] shrink-0 shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
            <div className="w-14 h-14 rounded-xl bg-slate-50 dark:bg-slate-900 flex items-center justify-center shrink-0 border border-slate-100 dark:border-slate-800">
                {icon}
            </div>
            <div>
                <h4 className="font-bold text-slate-900 dark:text-white text-base mb-1">{name}</h4>
                <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{desc}</p>
            </div>
        </div>
    );
}

