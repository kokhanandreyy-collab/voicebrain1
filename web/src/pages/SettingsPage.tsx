import { useState, useEffect } from 'react';
import { ArrowLeft, Plug, Zap, X, Loader2, Lock, Download, Trash, AlertTriangle } from 'lucide-react';
import { Link, useSearchParams, useParams } from 'react-router-dom';
import api from '../api';
import { Button } from '../components/ui';
import { TagManager } from '../components/TagManager';
import { Integration } from '../types';

interface AvailableIntegration {
    id: string;
    name: string;
    category: string;
    desc: string;
    bg: string;
    text: string;
    icon: string;
    isPremium?: boolean;
}

const CATEGORIES = ["All", "Tasks", "Notes", "Communication", "Storage"];

export default function SettingsPage() {
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [availableIntegrations, setAvailableIntegrations] = useState<AvailableIntegration[]>([]);
    const [loading, setLoading] = useState(false);
    const [userTier, setUserTier] = useState<string>('free');

    // Filter Stats
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('All');

    // Zapier Modal State
    const [isZapierModalOpen, setIsZapierModalOpen] = useState(false);
    const [zapierWebhookUrl, setZapierWebhookUrl] = useState('');
    const [zapierAutoTrigger, setZapierAutoTrigger] = useState(true);
    const [savingZapier, setSavingZapier] = useState(false);
    const [activeTab, setActiveTab] = useState<'integrations' | 'tags' | 'privacy' | 'personalization'>('integrations');

    // Personalization State
    const [userBio, setUserBio] = useState('');
    const [targetLanguage, setTargetLanguage] = useState('Original');
    const [savingBio, setSavingBio] = useState(false);

    // Privacy State
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    // Auth Flow State
    const [searchParams] = useSearchParams();
    const { provider: routeProvider } = useParams();

    useEffect(() => {
        fetchSettings();
        fetchUser();
        fetchConfig(); // Fetch available list
        handleCallback();
    }, [searchParams, routeProvider]);

    const fetchUser = async () => {
        try {
            const { data } = await api.get('/auth/me');
            setUserTier(data.tier || 'free');

            try {
                const profileReq = await api.get('/users/me');
                if (profileReq.data.bio) setUserBio(profileReq.data.bio);
                if (profileReq.data.target_language) setTargetLanguage(profileReq.data.target_language);
            } catch (err) {
                console.log("Could not fetch extended profile", err);
            }
        } catch (e) {
            console.error("Failed to fetch user", e);
        }
    };

    const handleSaveBio = async () => {
        setSavingBio(true);
        try {
            // Using new /users/me endpoint
            await api.put('/users/me', {
                bio: userBio,
                target_language: targetLanguage
            });
            alert("Personalization settings saved!");
        } catch (error) {
            console.error(error);
            alert("Failed to save settings.");
        } finally {
            setSavingBio(false);
        }
    };

    const fetchConfig = async () => {
        try {
            const { data } = await api.get('/integrations/config');
            setAvailableIntegrations(data);
        } catch (error) {
            console.error("Failed to fetch integration config", error);
        }
    };

    const fetchSettings = async () => {
        try {
            const { data } = await api.get('/integrations');
            setIntegrations(data);

            // Pre-fill Zapier if exists
            const zap = data.find((i: any) => i.provider === 'zapier');
            if (zap) {
                setZapierWebhookUrl(zap.settings?.webhook_url || zap.access_token || '');
                setZapierAutoTrigger(zap.settings?.auto_trigger_new_note ?? true);
            }

            // Pre-fill Weeek
            const weeek = data.find((i: any) => i.provider === 'weeek');
            if (weeek) {
                setWeeekToken(weeek.settings?.api_key || '');
            }

            // Pre-fill Bitrix
            const bitrix = data.find((i: any) => i.provider === 'bitrix24');
            if (bitrix) {
                setBitrixWebhookUrl(bitrix.settings?.webhook_url || '');
            }

            // Pre-fill Kaiten
            const kaiten = data.find((i: any) => i.provider === 'kaiten');
            if (kaiten) {
                setKaitenToken(kaiten.settings?.api_key || '');
                setKaitenBoardId(kaiten.settings?.board_id || '');
            }
        } catch (error) {
            console.error(error);
        }
    };

    const handleCallback = async () => {
        const code = searchParams.get('code');
        const provider = searchParams.get('provider') || routeProvider;
        const referer = searchParams.get('referer');

        if (code && provider) {
            // Remove params from URL to avoid re-trigger
            window.history.replaceState({}, document.title, window.location.pathname);

            setLoading(true);
            try {
                await api.post('/integrations/callback', { provider, code, referer });
                await fetchSettings();
                alert(`Successfully connected to ${provider.toUpperCase()}!`);
            } catch (error) {
                alert("Failed to connect integration.");
            } finally {
                setLoading(false);
            }
        }
    };

    const connectProvider = async (provider: string, isPremium: boolean = false) => {
        if (isPremium && userTier === 'free') {
            alert("This integration is available on Premium plan.");
            return;
        }

        if (provider === 'zapier') {
            setIsZapierModalOpen(true);
            return;
        }

        if (provider === 'weeek') {
            setIsWeeekModalOpen(true);
            return;
        }

        if (provider === 'bitrix24') {
            setIsBitrixModalOpen(true);
            return;
        }

        if (provider === 'kaiten') {
            setIsKaitenModalOpen(true);
            return;
        }

        try {
            const { data } = await api.get(`/integrations/${provider}/auth-url`);
            window.location.href = data.url;
        } catch (error) {
            alert("Could not start auth flow");
        }
    };

    const handleSaveZapier = async () => {
        if (!zapierWebhookUrl.startsWith('http')) {
            alert("Please enter a valid URL starting with http/https");
            return;
        }

        setSavingZapier(true);
        try {
            await api.post('/integrations', {
                provider: 'zapier',
                credentials: {
                    webhook_url: zapierWebhookUrl,
                    auto_trigger_new_note: zapierAutoTrigger
                }
            });
            await fetchSettings();
            setIsZapierModalOpen(false);
            alert("Zapier integration saved!");
        } catch (error) {
            console.error(error);
            alert("Failed to save Zapier settings");
        } finally {
            setSavingZapier(false);
        }
    };

    const handleSaveWeeek = async () => {
        if (weeekToken.length < 10) {
            alert("Please enter a valid WEEEK API Token");
            return;
        }
        setSavingWeeek(true);
        try {
            await api.post('/integrations', {
                provider: 'weeek',
                credentials: {
                    api_key: weeekToken
                }
            });
            await fetchSettings();
            setIsWeeekModalOpen(false);
            alert("WEEEK integration saved!");
        } catch (error) {
            console.error(error);
            alert("Failed to save WEEEK settings");
        } finally {
            setSavingWeeek(false);
        }
    };

    const handleSaveBitrix = async () => {
        if (!bitrixWebhookUrl.startsWith('http')) {
            alert("Please enter a valid Bitrix24 Webhook URL");
            return;
        }
        setSavingBitrix(true);
        try {
            await api.post('/integrations', {
                provider: 'bitrix24',
                credentials: {
                    webhook_url: bitrixWebhookUrl
                }
            });
            await fetchSettings();
            setIsBitrixModalOpen(false);
            alert("Bitrix24 integration saved!");
        } catch (error) {
            console.error(error);
            alert("Failed to save Bitrix24 settings");
        } finally {
            setSavingBitrix(false);
        }
    };

    // Auth Flow State
    const [isWeeekModalOpen, setIsWeeekModalOpen] = useState(false);
    const [weeekToken, setWeeekToken] = useState('');
    const [savingWeeek, setSavingWeeek] = useState(false);

    const [isBitrixModalOpen, setIsBitrixModalOpen] = useState(false);
    const [bitrixWebhookUrl, setBitrixWebhookUrl] = useState('');
    const [savingBitrix, setSavingBitrix] = useState(false);

    const [isKaitenModalOpen, setIsKaitenModalOpen] = useState(false);
    const [kaitenToken, setKaitenToken] = useState('');
    const [kaitenBoardId, setKaitenBoardId] = useState('');
    const [kaitenBoards, setKaitenBoards] = useState<any[]>([]);
    const [loadingBoards, setLoadingBoards] = useState(false);
    const [savingKaiten, setSavingKaiten] = useState(false);

    const fetchKaitenBoards = async () => {
        if (!kaitenToken) return;
        setLoadingBoards(true);
        try {
            const { data } = await api.post('/integrations/kaiten/boards', { api_key: kaitenToken });
            setKaitenBoards(data);
            // Auto-select first if available
            if (data.length > 0 && !kaitenBoardId) {
                setKaitenBoardId(data[0].id);
            }
        } catch (error) {
            console.error(error);
            alert("Failed to fetch boards. Check token.");
        } finally {
            setLoadingBoards(false);
        }
    };

    const handleSaveKaiten = async () => {
        if (!kaitenToken || !kaitenBoardId) {
            alert("Please enter API Key and Select a Board");
            return;
        }
        setSavingKaiten(true);
        try {
            await api.post('/integrations', {
                provider: 'kaiten',
                credentials: {
                    api_key: kaitenToken,
                    board_id: kaitenBoardId
                }
            });
            await fetchSettings();
            setIsKaitenModalOpen(false);
            alert("Kaiten integration saved!");
        } catch (error) {
            console.error(error);
            alert("Failed to save Kaiten settings");
        } finally {
            setSavingKaiten(false);
        }
    };

    // In fetchSettings, pre-fill weeek
    // Note: React state should be at top level but doing quick injection for speed.
    // I should move state up.

    const disconnectProvider = async (provider: string) => {
        if (!confirm(`Disconnect ${provider}?`)) return;
        try {
            await api.delete(`/integrations/${provider}`);
            setIntegrations(integrations.filter(i => i.provider !== provider));
            if (provider === 'zapier') {
                setZapierWebhookUrl('');
                setZapierAutoTrigger(true);
            }
        } catch (error) {
            alert("Failed to disconnect");
        }
    };

    const handleExportData = async () => {
        setIsExporting(true);
        try {
            const { data } = await api.get('/exports/all', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `voicebrain_export_${new Date().toISOString().split('T')[0]}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            alert("Failed to export data");
        } finally {
            setIsExporting(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirmation !== 'DELETE') return;

        setIsDeleting(true);
        try {
            await api.delete('/auth/me');
            localStorage.removeItem('token');
            window.location.href = '/login';
        } catch (error) {
            alert("Failed to delete account");
            setIsDeleting(false);
        }
    };

    const filteredIntegrations = availableIntegrations.filter(item => {
        const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.desc.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = selectedCategory === 'All' || item.category === selectedCategory;
        return matchesSearch && matchesCategory;
    });

    const getIntegration = (provider: string) => integrations.find(i => i.provider === provider);

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-12">
            <div className="max-w-6xl mx-auto space-y-8">
                <Link to="/dashboard" className="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-brand-blue dark:hover:text-blue-400 transition-colors">
                    <ArrowLeft size={20} /> Back to Dashboard
                </Link>

                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-2">
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Settings</h1>
                        <p className="text-slate-500 dark:text-slate-400">Manage your connected apps and organizational system.</p>
                    </div>

                    <div className="flex bg-white dark:bg-slate-900 p-1 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                        <button
                            onClick={() => setActiveTab('integrations')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'integrations' ? 'bg-brand-blue text-white' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'}`}
                        >
                            Integrations
                        </button>
                        <button
                            onClick={() => setActiveTab('tags')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'tags' ? 'bg-brand-blue text-white' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'}`}
                        >
                            Tag Manager
                        </button>
                        <button
                            onClick={() => setActiveTab('personalization')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'personalization' ? 'bg-brand-blue text-white' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'}`}
                        >
                            Personalization
                        </button>
                        <button
                            onClick={() => setActiveTab('privacy')}
                            className={`px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'privacy' ? 'bg-brand-blue text-white' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300'}`}
                        >
                            Data & Privacy
                        </button>
                    </div>
                </div>

                {activeTab === 'integrations' ? (
                    <>
                        <div className="flex items-center justify-between gap-6">
                            <div className="w-full md:w-80">
                                <div className="relative">
                                    <input
                                        type="text"
                                        placeholder="Search integrations..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue outline-none transition-all text-sm dark:text-white"
                                    />
                                    <Plug className="absolute left-3 top-2.5 text-slate-400" size={18} />
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
                            {CATEGORIES.map(cat => (
                                <button
                                    key={cat}
                                    onClick={() => setSelectedCategory(cat)}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${selectedCategory === cat
                                        ? 'bg-brand-blue text-white shadow-md shadow-blue-500/20'
                                        : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                                        }`}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredIntegrations.map((item) => {
                                const isConnected = !!getIntegration(item.id);
                                const isLocked = item.isPremium && userTier !== 'premium';

                                return (
                                    <div key={item.id} className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 hover:shadow-md transition-all flex flex-col justify-between">
                                        <div className="space-y-4">
                                            <div className="flex items-start justify-between">
                                                <div className={`w-14 h-14 ${item.bg} rounded-2xl flex items-center justify-center relative shadow-sm`}>
                                                    <span className={`font-bold text-xl ${item.text}`}>{item.icon}</span>
                                                    {isLocked && <div className="absolute -top-1 -right-1 bg-slate-800 text-white rounded-full p-1 border-2 border-white dark:border-slate-900"><Lock size={10} /></div>}
                                                </div>
                                                {isConnected && (
                                                    getIntegration(item.id)?.status === 'auth_error' ? (
                                                        <span className="flex items-center gap-1.5 bg-red-50 text-red-600 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider cursor-help" title={getIntegration(item.id)?.error_message}>
                                                            <div className="w-1 h-1 rounded-full bg-red-500 animate-pulse" />
                                                            Auth Error
                                                        </span>
                                                    ) : (
                                                        <span className="flex items-center gap-1.5 bg-emerald-50 text-emerald-600 text-[10px] px-2 py-1 rounded-full font-bold uppercase tracking-wider">
                                                            <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                                                            Active
                                                        </span>
                                                    )
                                                )}
                                            </div>

                                            <div>
                                                <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                                    {item.name}
                                                    {item.isPremium && <span title="Premium Feature"><Zap size={14} className="text-amber-500 fill-amber-500" /></span>}
                                                </h3>
                                                <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed min-h-[40px]">
                                                    {isConnected && item.id === 'zapier'
                                                        ? 'Service connected via Webhook'
                                                        : isConnected
                                                            ? `Connected to ${getIntegration(item.id)?.settings?.workspace_name || 'workspace'}`
                                                            : item.desc
                                                    }
                                                </p>
                                            </div>
                                        </div>

                                        <div className="pt-6 mt-4 border-t border-slate-50 dark:border-slate-800 flex items-center justify-between">
                                            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{item.category}</div>
                                            {isConnected ? (
                                                <div className="flex items-center gap-3">
                                                    {getIntegration(item.id)?.status === 'auth_error' && (
                                                        <button
                                                            onClick={() => connectProvider(item.id, item.isPremium)}
                                                            className="text-brand-blue font-bold text-xs hover:underline flex items-center gap-1"
                                                        >
                                                            Reconnect
                                                        </button>
                                                    )}
                                                    {item.id === 'zapier' && (
                                                        <button onClick={() => setIsZapierModalOpen(true)} className="text-brand-blue font-bold text-xs hover:underline">
                                                            Config
                                                        </button>
                                                    )}
                                                    <button onClick={() => disconnectProvider(item.id)} className="text-red-500 font-bold text-xs hover:bg-red-50 dark:hover:bg-red-900/30 px-2 py-1 rounded-md transition-colors">
                                                        Remove
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    onClick={() => connectProvider(item.id, item.isPremium)}
                                                    className={`px-4 py-2 ${isConnected ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400' : 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm shadow-slate-900/10'} text-xs font-bold rounded-lg hover:translate-y-[-1px] transition-all flex items-center gap-2 ${isLocked ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                >
                                                    {isLocked ? <Lock size={12} /> : null}
                                                    Connect
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {filteredIntegrations.length === 0 && (
                            <div className="text-center py-20 bg-white dark:bg-slate-900 rounded-3xl border border-dashed border-slate-300 dark:border-slate-700">
                                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
                                    <Plug size={32} />
                                </div>
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">No integrations found</h3>
                                <p className="text-slate-500 dark:text-slate-400">Try adjusting your search or category filter.</p>
                                <Button variant="ghost" className="mt-4" onClick={() => { setSearchQuery(''); setSelectedCategory('All'); }}>
                                    Clear all filters
                                </Button>
                            </div>
                        )}
                    </>
                ) : activeTab === 'tags' ? (
                    <TagManager />
                ) : activeTab === 'personalization' ? (
                    <div className="max-w-2xl mx-auto space-y-8 animate-in fade-in duration-300">
                        <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-soft">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="w-12 h-12 bg-purple-50 dark:bg-purple-900/20 rounded-2xl flex items-center justify-center text-purple-600 dark:text-purple-400">
                                    <Zap size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold dark:text-white">AI Personalization</h2>
                                    <p className="text-slate-500 text-sm">Teach VoiceBrain about you.</p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                                    Your Bio & Context
                                </label>
                                <p className="text-xs text-slate-500 mb-2">
                                    Describe your job, family members, frequent projects, or specific jargon.
                                    The AI will use this to improve name recognition and categorize your notes accurately.
                                </p>
                                <textarea
                                    value={userBio}
                                    onChange={(e) => setUserBio(e.target.value)}
                                    placeholder="e.g. I am a Software Engineer at TechCorp. My wife is Sarah. I'm working on Project Apollo using React and Python. I like running and cooking."
                                    className="w-full h-40 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-base leading-relaxed text-slate-900 dark:text-white resize-none"
                                />

                                <div className="flex justify-end pt-4">
                                    <Button
                                        onClick={handleSaveBio}
                                        disabled={savingBio}
                                        className="bg-brand-blue hover:bg-blue-600 text-white px-8 h-12 rounded-xl shadow-lg shadow-blue-500/20"
                                    >
                                        {savingBio ? <Loader2 className="animate-spin" /> : 'Save Context'}
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {/* Language Settings */}
                        <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-soft">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="w-12 h-12 bg-blue-50 dark:bg-blue-900/20 rounded-2xl flex items-center justify-center text-blue-600 dark:text-blue-400">
                                    <div className="font-bold text-lg">Aa</div>
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold dark:text-white">Output Language</h2>
                                    <p className="text-slate-500 text-sm">Always generate titles & summaries in this language.</p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">
                                    Target Language
                                </label>
                                <select
                                    value={targetLanguage}
                                    onChange={(e) => setTargetLanguage(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-base text-slate-900 dark:text-white appearance-none cursor-pointer"
                                >
                                    <option value="Original">Original (Same as Audio)</option>
                                    <option value="English">English</option>
                                    <option value="Russian">Russian</option>
                                    <option value="Spanish">Spanish</option>
                                    <option value="French">French</option>
                                    <option value="German">German</option>
                                    <option value="Portuguese">Portuguese</option>
                                    <option value="Italian">Italian</option>
                                    <option value="Japanese">Japanese</option>
                                    <option value="Chinese">Chinese</option>
                                </select>
                                <p className="text-xs text-slate-500">
                                    VoiceBrain will automatically translate your insights regardless of the spoken language.
                                </p>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="max-w-2xl mx-auto space-y-8">
                        <div className="bg-white dark:bg-slate-900 p-8 rounded-[32px] border border-slate-100 dark:border-slate-800 shadow-soft">
                            <h2 className="text-xl font-bold flex items-center gap-2 mb-6 dark:text-white">
                                <Download size={24} className="text-brand-blue" /> Export Data
                            </h2>
                            <p className="text-slate-500 dark:text-slate-400 mb-8 leading-relaxed">
                                Download a complete copy of all your notes, transcriptions, and metadata in JSON format.
                                You can use this to backup your data or migrate to another service.
                            </p>

                            <Button onClick={handleExportData} disabled={isExporting} className="w-full sm:w-auto flex items-center gap-2">
                                {isExporting ? <Loader2 className="animate-spin" /> : <Download size={18} />}
                                Download All Data
                            </Button>
                        </div>

                        <div className="bg-red-50 dark:bg-red-900/10 p-8 rounded-[32px] border border-red-100 dark:border-red-900/30">
                            <h2 className="text-xl font-bold flex items-center gap-2 mb-6 text-red-600 dark:text-red-400">
                                <AlertTriangle size={24} /> Danger Zone
                            </h2>
                            <p className="text-red-600/80 dark:text-red-400/80 mb-8 leading-relaxed">
                                Permanently delete your account and all associated data. This action cannot be undone.
                                All your notes, audio files, and settings will be wiped from our servers immediately.
                            </p>

                            <Button
                                onClick={() => setIsDeleteModalOpen(true)}
                                variant="outline"
                                className="w-full sm:w-auto border-red-200 text-red-600 hover:bg-red-100 hover:text-red-700 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/30"
                            >
                                <Trash size={18} className="mr-2" />
                                Delete Account
                            </Button>
                        </div>
                    </div>
                )}
            </div>

            {/* KAITEN CONFIG MODAL */}
            {isKaitenModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsKaitenModalOpen(false)} />
                    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50 animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold flex items-center gap-2 dark:text-white"><div className="w-8 h-8 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 flex items-center justify-center font-bold text-lg">K</div> Connect Kaiten</h3>
                            <button onClick={() => setIsKaitenModalOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" /></button>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">My Kaiten API Key</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={kaitenToken}
                                        onChange={(e) => setKaitenToken(e.target.value)}
                                        placeholder="put-your-token-here"
                                        className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm font-mono text-slate-600 dark:text-slate-300"
                                    />
                                    <Button onClick={fetchKaitenBoards} disabled={loadingBoards || !kaitenToken} variant="outline" className="h-[46px] whitespace-nowrap">
                                        {loadingBoards ? <Loader2 size={16} className="animate-spin" /> : 'Load Boards'}
                                    </Button>
                                </div>
                                <p className="text-xs text-slate-400 mt-2">
                                    Settings &rarr; API Keys.
                                </p>
                            </div>

                            {kaitenBoards.length > 0 && (
                                <div>
                                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Select Board</label>
                                    <select
                                        value={kaitenBoardId}
                                        onChange={(e) => setKaitenBoardId(e.target.value)}
                                        className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm text-slate-600 dark:text-slate-300 appearance-none cursor-pointer"
                                    >
                                        <option value="">-- Choose a Board --</option>
                                        {kaitenBoards.map((b: any) => (
                                            <option key={b.id} value={b.id}>{b.title}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            <Button
                                onClick={handleSaveKaiten}
                                disabled={savingKaiten || !kaitenBoardId}
                                className="w-full h-12 text-base bg-yellow-500 hover:bg-yellow-600 text-white rounded-xl shadow-lg shadow-yellow-500/20"
                            >
                                {savingKaiten ? <Loader2 className="animate-spin" /> : 'Save Configuration'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* ZAPIER CONFIG MODAL */}
            {isZapierModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsZapierModalOpen(false)} />
                    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50 animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold flex items-center gap-2 dark:text-white"><div className="w-8 h-8 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 flex items-center justify-center font-bold text-lg">Z</div> Connect Zapier</h3>
                            <button onClick={() => setIsZapierModalOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" /></button>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Zapier Webhook URL</label>
                                <input
                                    type="text"
                                    value={zapierWebhookUrl}
                                    onChange={(e) => setZapierWebhookUrl(e.target.value)}
                                    placeholder="https://hooks.zapier.com/hooks/catch/..."
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm font-mono text-slate-600 dark:text-slate-300"
                                />
                                <p className="text-xs text-slate-400 mt-2">
                                    Create a "Catch Hook" trigger in Zapier and paste the URL here.
                                </p>
                            </div>

                            <div className="flex items-center gap-3 p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700">
                                <div className={`w-10 h-6 rounded-full p-1 cursor-pointer transition-colors ${zapierAutoTrigger ? 'bg-green-500' : 'bg-slate-300'}`} onClick={() => setZapierAutoTrigger(!zapierAutoTrigger)}>
                                    <div className={`w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${zapierAutoTrigger ? 'translate-x-4' : 'translate-x-0'}`} />
                                </div>
                                <div>
                                    <h4 className="font-bold text-sm text-slate-900 dark:text-white">Auto-send new notes</h4>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">Automatically trigger this webhook when processing is complete.</p>
                                </div>
                            </div>

                            <Button
                                onClick={handleSaveZapier}
                                disabled={savingZapier || !zapierWebhookUrl}
                                className="w-full h-12 text-base bg-orange-500 hover:bg-orange-600 text-white rounded-xl shadow-lg shadow-orange-500/20"
                            >
                                {savingZapier ? <Loader2 className="animate-spin" /> : 'Save Configuration'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* BITRIX24 CONFIG MODAL */}
            {isBitrixModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsBitrixModalOpen(false)} />
                    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50 animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold flex items-center gap-2 dark:text-white"><div className="w-8 h-8 rounded bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 flex items-center justify-center font-bold text-lg">B</div> Connect Bitrix24</h3>
                            <button onClick={() => setIsBitrixModalOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" /></button>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Bitrix24 Inbound Webhook</label>
                                <input
                                    type="text"
                                    value={bitrixWebhookUrl}
                                    onChange={(e) => setBitrixWebhookUrl(e.target.value)}
                                    placeholder="https://b24-xxxx.bitrix24.ru/rest/1/hook_key/"
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm font-mono text-slate-600 dark:text-slate-300"
                                />
                                <p className="text-xs text-slate-400 mt-2">
                                    Create a webhook with access to <b>CRM</b> and <b>Tasks</b> in Developer Resources.
                                </p>
                            </div>

                            <Button
                                onClick={handleSaveBitrix}
                                disabled={savingBitrix || !bitrixWebhookUrl}
                                className="w-full h-12 text-base bg-cyan-500 hover:bg-cyan-600 text-white rounded-xl shadow-lg shadow-cyan-500/20"
                            >
                                {savingBitrix ? <Loader2 className="animate-spin" /> : 'Save Configuration'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* WEEEK CONFIG MODAL */}
            {isWeeekModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsWeeekModalOpen(false)} />
                    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50 animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold flex items-center gap-2 dark:text-white"><div className="w-8 h-8 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-lg">W</div> Connect WEEEK</h3>
                            <button onClick={() => setIsWeeekModalOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" /></button>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">WEEEK API Token</label>
                                <input
                                    type="text"
                                    value={weeekToken}
                                    onChange={(e) => setWeeekToken(e.target.value)}
                                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cci..."
                                    className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/50 text-sm font-mono text-slate-600 dark:text-slate-300"
                                />
                                <p className="text-xs text-slate-400 mt-2">
                                    Get your token from <a href="https://weeek.net/app/settings/integrations" target="_blank" rel="noopener noreferrer" className="text-brand-blue hover:underline">WEEEK Settings</a>.
                                </p>
                            </div>

                            <Button
                                onClick={handleSaveWeeek}
                                disabled={savingWeeek || weeekToken.length < 10}
                                className="w-full h-12 text-base bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-lg shadow-blue-500/20"
                            >
                                {savingWeeek ? <Loader2 className="animate-spin" /> : 'Save Configuration'}
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* DELETE ACCOUNT MODAL */}
            {isDeleteModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-red-900/30 backdrop-blur-sm" onClick={() => setIsDeleteModalOpen(false)} />
                    <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50 animate-in fade-in zoom-in duration-200 border-2 border-red-500">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold flex items-center gap-2 text-red-600">
                                <AlertTriangle size={24} /> Delete Account?
                            </h3>
                            <button onClick={() => setIsDeleteModalOpen(false)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200" /></button>
                        </div>

                        <div className="space-y-6">
                            <p className="text-slate-600 dark:text-slate-300">
                                This action is <strong>irreversible</strong>. All your notes, recordings, and settings will be permanently lost.
                            </p>
                            <div>
                                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                                    Type <span className="font-mono text-red-600">DELETE</span> to confirm
                                </label>
                                <input
                                    type="text"
                                    value={deleteConfirmation}
                                    onChange={(e) => setDeleteConfirmation(e.target.value)}
                                    placeholder="DELETE"
                                    className="w-full px-4 py-3 rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/10 focus:outline-none focus:ring-2 focus:ring-red-500 text-sm font-bold text-red-600 placeholder:text-red-300"
                                />
                            </div>

                            <button
                                onClick={handleDeleteAccount}
                                disabled={deleteConfirmation !== 'DELETE' || isDeleting}
                                className="w-full h-12 text-base font-bold bg-red-600 hover:bg-red-700 disabled:bg-slate-200 dark:disabled:bg-slate-800 disabled:text-slate-400 text-white rounded-xl shadow-lg shadow-red-500/20 transition-all flex items-center justify-center gap-2"
                            >
                                {isDeleting ? <Loader2 className="animate-spin" /> : 'Confirm Deletion'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {loading && (
                <div className="fixed inset-0 bg-white/50 backdrop-blur-sm z-50 flex items-center justify-center">
                    <div className="bg-white p-6 rounded-xl shadow-xl flex items-center gap-3">
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-brand-blue border-t-transparent" />
                        <span className="font-medium">Connecting...</span>
                    </div>
                </div>
            )}
        </div>
    );
}
