import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Mail, Calendar, MessageSquare, FileText, Share2, Check, ListTodo, Activity, FileEdit, Apple, Lock, Cloud, Database } from 'lucide-react';
import { Note } from '../types';
import api from '../api';

interface ShareModalProps {
    isOpen: boolean;
    onClose: () => void;
    note: Note | null;
    initialProvider?: string;
}

export function ShareModal({ isOpen, onClose, note, initialProvider }: ShareModalProps) {
    const [sharingTo, setSharingTo] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);
    const [healthData, setHealthData] = useState<Record<string, string> | null>(null);
    const [showObsidianFallback, setShowObsidianFallback] = useState(false);
    const [userTier, setUserTier] = useState<string>('free');
    const [connectedApps, setConnectedApps] = useState<Set<string>>(new Set());

    // Fetch User Tier and Integrations
    useEffect(() => {
        if (isOpen) {
            Promise.all([
                api.get('/users/me'),
                api.get('/integrations')
            ]).then(([userRes, intRes]) => {
                setUserTier(userRes.data.tier || 'free');
                const apps = new Set<string>(intRes.data.map((i: any) => i.provider));
                setConnectedApps(apps);
            }).catch(err => console.error("Failed to fetch user context", err));

            if (initialProvider) {
                setSuccessMsg(`Retrying ${initialProvider}...`);
                setTimeout(() => setSuccessMsg(null), 3000);
            }
        }
    }, [isOpen, initialProvider]);

    const isPro = userTier === 'pro' || userTier === 'premium';

    const copyToClipboard = () => {
        if (!note) return;
        const text = `# ${note.title || 'Untitled'}\n\n${note.summary || ''}\n\n## Transcript\n${note.transcription_text || ''}\n\nTags: ${(note.tags || []).join(', ')}`;
        navigator.clipboard.writeText(text);
        showSuccess("Copied to clipboard!");
    };

    const sendEmail = () => {
        if (!note) return;
        const subject = encodeURIComponent(note.title || "VoiceBrain Note");
        const body = encodeURIComponent(`${note.summary || ''}\n\nTranscript:\n${note.transcription_text || ''}`);
        window.open(`mailto:?subject=${subject}&body=${body}`);
        onClose();
    };

    // Apple Notes Strategy: Email (Safest) & Copy
    const emailToAppleNotes = () => {
        if (!note) return;
        const subject = encodeURIComponent(note.title || "VoiceBrain Note");

        let bodyText = `${note.summary || ''}\n\nTranscript:\n${note.transcription_text || ''}\n\n#${(note.tags || []).join(' #')}`;
        // Add Audio Link if available
        if (note.audio_url) {
            bodyText += `\n\nAudio: ${note.audio_url}`;
        }

        const body = encodeURIComponent(bodyText);
        window.open(`mailto:?subject=${subject}&body=${body}`);
        onClose();
    };

    // Obsidian Strategy: URI or Download
    const openInObsidian = () => {
        if (!note) return;
        setShowObsidianFallback(false);

        const frontmatter = [
            '---',
            `date: ${new Date(note.created_at).toISOString().split('T')[0]}`,
            `tags: [${(note.tags || []).join(', ')}]`,
            `mood: ${note.mood || 'Neutral'}`,
            '---'
        ].join('\n');

        const content = `${frontmatter}\n\n# ${note.title}\n\n${note.summary}\n\n## Transcript\n${note.transcription_text}`;

        const encodedName = encodeURIComponent(note.title || 'Untitled Note');
        const encodedContent = encodeURIComponent(content);

        // Try opening Obsidian
        window.location.href = `obsidian://new?name=${encodedName}&content=${encodedContent}`;
        showSuccess("Opening Obsidian...");

        // Fallback check logic
        setTimeout(() => {
            setShowObsidianFallback(true);
        }, 1500);
    };

    const openInThings3 = () => {
        if (!note) return;
        if (!isPro) {
            alert("Things 3 integration is a Pro feature.");
            return;
        }
        const encodedTitle = encodeURIComponent(note.title || 'Voice Note');
        const encodedNotes = encodeURIComponent(`${note.summary}\n\n${note.transcription_text || ''}`);
        window.location.href = `things:///add?title=${encodedTitle}&notes=${encodedNotes}`;
        showSuccess("Opened in Things 3");
    };

    const downloadMarkdown = () => {
        if (!note) return;
        const frontmatter = [
            '---',
            `date: ${new Date(note.created_at).toISOString().split('T')[0]}`,
            `tags: [${(note.tags || []).join(', ')}]`,
            `mood: ${note.mood || 'Neutral'}`,
            '---'
        ].join('\n');

        const content = `${frontmatter}\n\n# ${note.title}\n\n${note.summary}\n\n## Transcript\n${note.transcription_text}`;

        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${(note.title || 'note').replace(/\s+/g, '_')}.md`;
        a.click();
        showSuccess("Downloaded Markdown");
    };

    const analyzeHealthData = async () => {
        if (!note) return;
        setSharingTo('health');
        try {
            const { data } = await api.post(`/notes/${note.id}/extract-health`);
            if (!data || Object.keys(data).length === 0) {
                showSuccess("No health metrics found.");
                setSharingTo(null);
                return;
            }
            setHealthData(data);
            setSharingTo(null);
        } catch (e) {
            alert("Analysis failed.");
            setSharingTo(null);
        }
    };

    const copyHealthData = () => {
        if (!healthData) return;
        const metrics = Object.entries(healthData).map(([k, v]) => `${k}: ${v}`).join('\n');
        navigator.clipboard.writeText(metrics);
        showSuccess("Copied metrics to clipboard!");
    };


    const downloadICS = () => {
        if (!note) return;
        const date = new Date(note.created_at);
        const endDate = new Date(date.getTime() + 60 * 60 * 1000);
        const formatDate = (d: Date) => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
        const icsContent = [
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'BEGIN:VEVENT',
            `DTSTART:${formatDate(date)}`, `DTEND:${formatDate(endDate)}`,
            `SUMMARY:${note.title || 'Voice Note'}`,
            `DESCRIPTION:${note.summary?.replace(/\n/g, '\\n') || ''}`,
            'END:VEVENT', 'END:VCALENDAR'
        ].join('\n');
        const blob = new Blob([icsContent], { type: 'text/calendar' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'event.ics';
        a.click();
        showSuccess("ICS file downloaded");
    };

    const shareToSocial = async () => {
        if (!note) return;
        if (navigator.share) {
            try {
                await navigator.share({
                    title: note.title || 'Voice Note',
                    text: note.summary || '',
                    url: window.location.href
                });
                onClose();
            } catch (err) { console.log("Share canceled"); }
        } else {
            copyToClipboard();
            alert("Web Share API not supported on this device. Copied to clipboard instead.");
        }
    };

    const shareToApp = async (provider: string, isProFeature = false) => {
        if (!note) return;

        if (isProFeature && !isPro) {
            alert("This feature requires Pro plan. Please upgrade.");
            return;
        }

        setSharingTo(provider);
        try {
            await api.post(`/notes/${note.id}/share/${provider}`);
            showSuccess(`Exported to ${provider} successfully!`);
        } catch (error: any) {
            alert(`Failed to export: ${error.response?.data?.detail || "Make sure you connected this app in Settings."}`);
        } finally {
            setSharingTo(null);
        }
    };

    const showSuccess = (msg: string) => {
        setSuccessMsg(msg);
        setTimeout(() => {
            setSuccessMsg(null);
            if (msg.includes("Exported")) onClose();
        }, 2500);
    };

    if (!isOpen || !note) return null;

    // Health Data View
    if (healthData) {
        return (
            <AnimatePresence>
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setHealthData(null)} />
                    <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="relative w-full max-w-sm bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden p-6 z-50">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold flex items-center gap-2 dark:text-white"><Activity className="text-red-500" /> Health Metrics</h3>
                            <button onClick={() => setHealthData(null)}><X size={20} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" /></button>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 mb-4 space-y-2">
                            {Object.entries(healthData).map(([key, value]) => (
                                <div key={key} className="flex justify-between items-center text-sm border-b border-slate-200 dark:border-slate-700 last:border-0 pb-2 last:pb-0">
                                    <span className="text-slate-500 dark:text-slate-400 font-medium">{key}</span>
                                    <span className="font-bold text-slate-800 dark:text-slate-100">{value}</span>
                                </div>
                            ))}
                        </div>
                        <button onClick={copyHealthData} className="w-full py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-semibold transition-colors flex items-center justify-center gap-2">
                            <Copy size={18} /> Copy All Metrics
                        </button>
                    </motion.div>
                </div>
            </AnimatePresence>
        )
    }

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-black/40 backdrop-blur-sm"
                    onClick={onClose}
                />
                <motion.div
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ scale: 0.95, opacity: 0, y: 20 }}
                    className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden max-h-[85vh] overflow-y-auto"
                >
                    <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800 sticky top-0 bg-white dark:bg-slate-900 z-10">
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">Share & Export</h3>
                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
                            <X size={20} className="text-slate-500 dark:text-slate-400" />
                        </button>
                    </div>

                    <div className="p-6 space-y-6">
                        {/* Quick Actions */}
                        <div className="grid grid-cols-2 gap-4">
                            <button onClick={copyToClipboard} className="flex flex-col items-center justify-center gap-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 transition-colors group border border-slate-100 dark:border-slate-800">
                                <Copy size={24} className="text-slate-400 group-hover:text-blue-500 dark:group-hover:text-blue-400" />
                                <span className="font-medium text-xs dark:text-slate-300">Copy Text</span>
                            </button>
                            <button onClick={shareToSocial} className="flex flex-col items-center justify-center gap-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 transition-colors group border border-slate-100 dark:border-slate-800">
                                <Share2 size={24} className="text-slate-400 group-hover:text-blue-500 dark:group-hover:text-blue-400" />
                                <span className="font-medium text-xs dark:text-slate-300">System Share</span>
                            </button>
                        </div>

                        {/* Integration Categories */}

                        {/* Apple Ecosystem */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                                <Apple size={12} /> Apple Ecosystem
                            </h4>
                            <div className="space-y-2">
                                <button onClick={emailToAppleNotes} className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 hover:border-yellow-200 dark:hover:border-yellow-900/40 transition-all text-left group">
                                    <div className="w-10 h-10 rounded-full bg-yellow-100 dark:bg-yellow-900/40 text-yellow-600 dark:text-yellow-400 flex items-center justify-center shrink-0"><FileText size={20} /></div>
                                    <div className="flex-1 min-w-0">
                                        <div className="font-semibold text-sm text-slate-900 dark:text-slate-100 group-hover:text-yellow-700 dark:group-hover:text-yellow-400">Add to Apple Notes</div>
                                        <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">Sends email to self (official sync method)</div>
                                    </div>
                                    <Check size={16} className="text-slate-300 dark:text-slate-600 opacity-0 group-hover:opacity-100" />
                                </button>
                                <button onClick={analyzeHealthData} className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-red-50 dark:hover:bg-red-900/20 hover:border-red-200 dark:hover:border-red-900/40 transition-all text-left group">
                                    <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 flex items-center justify-center shrink-0"><Activity size={20} /></div>
                                    <div className="flex-1 min-w-0">
                                        <div className="font-semibold text-sm text-slate-900 dark:text-slate-100 group-hover:text-red-700 dark:group-hover:text-red-400">Extract Health Data</div>
                                        <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">Finds steps, weight, sleep & calories</div>
                                    </div>
                                    {sharingTo === 'health' && <span className="animate-spin text-xs">⏳</span>}
                                </button>
                            </div>
                        </div>

                        {/* Second Brain & Notes */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                                <FileEdit size={12} /> Second Brain & Notes
                            </h4>
                            <div className="grid grid-cols-2 gap-3 mb-2">
                                {/* Reflect */}
                                <button onClick={() => shareToApp('reflect', true)} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <div className="w-5 h-5 rounded bg-indigo-500 text-white flex items-center justify-center font-bold text-[10px]">R</div>
                                    <div className="text-left">
                                        <div className="font-bold">Reflect</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">Append Note</div>
                                    </div>
                                    {connectedApps.has('reflect') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Craft */}
                                <button onClick={() => shareToApp('craft', true)} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <div className="w-5 h-5 rounded bg-orange-500 text-white flex items-center justify-center font-bold text-[10px]">C</div>
                                    <div className="text-left">
                                        <div className="font-bold">Craft</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">New Doc</div>
                                    </div>
                                    {connectedApps.has('craft') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Obsidian */}
                                <button onClick={openInObsidian} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:border-purple-200 dark:hover:border-purple-900/40 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <img src="https://upload.wikimedia.org/wikipedia/commons/1/10/2023_Obsidian_logo.svg" className="w-5 h-5" alt="Obsidian" />
                                    <div className="text-left">
                                        <div className="font-bold">Obsidian</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">via URI</div>
                                    </div>
                                </button>
                                {/* Notion */}
                                <button
                                    onClick={() => shareToApp('notion', true)}
                                    className={`flex items-center gap-2 p-3 rounded-lg border transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative ${initialProvider === 'notion' ? 'border-brand-blue bg-blue-50 dark:bg-blue-900/20 ring-2 ring-brand-blue/20' : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                                >
                                    <FileText size={20} className="text-slate-400 dark:text-slate-500" />
                                    <div className="text-left">
                                        <div className="font-bold">Notion</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">Create Page</div>
                                    </div>
                                    {connectedApps.has('notion') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Evernote */}
                                <button onClick={() => shareToApp('evernote', true)} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <div className="w-5 h-5 rounded bg-green-500 text-white flex items-center justify-center font-bold text-[10px]">E</div>
                                    <div className="text-left">
                                        <div className="font-bold">Evernote</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">New Note</div>
                                    </div>
                                    {connectedApps.has('evernote') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Readwise */}
                                <button onClick={() => shareToApp('readwise', true)} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <div className="w-5 h-5 rounded bg-yellow-500 text-white flex items-center justify-center font-bold text-[10px]">Rw</div>
                                    <div className="text-left">
                                        <div className="font-bold">Readwise</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">Save to Reader</div>
                                    </div>
                                    {connectedApps.has('readwise') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Keep */}
                                <button onClick={() => shareToApp('google_keep', true)} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full relative">
                                    <div className="w-5 h-5 rounded bg-yellow-400 text-white flex items-center justify-center font-bold text-[10px]">K</div>
                                    <div className="text-left">
                                        <div className="font-bold">Keep</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">Create Note</div>
                                    </div>
                                    {connectedApps.has('google_keep') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Markdown */}
                                <button onClick={downloadMarkdown} className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-all text-xs font-semibold text-slate-700 dark:text-slate-300 h-full">
                                    <div className="text-left">
                                        <div className="font-bold">Save .md</div>
                                        <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">Download</div>
                                    </div>
                                </button>
                            </div>

                            {/* Fallback Message for Obsidian */}
                            <AnimatePresence>
                                {showObsidianFallback && (
                                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="overflow-hidden">
                                        <div className="flex items-center justify-between bg-purple-50 dark:bg-purple-900/20 text-purple-800 dark:text-purple-300 text-xs p-3 rounded-lg mb-2">
                                            <span>Did it open? If not:</span>
                                            <button onClick={downloadMarkdown} className="underline font-bold hover:text-purple-600 dark:hover:text-purple-400">Download .md file (Automatic Fallback)</button>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Task Managers */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                                <ListTodo size={12} /> Task Managers
                            </h4>
                            <div className="grid grid-cols-2 gap-3">
                                {/* Things 3 */}
                                <button
                                    onClick={openInThings3}
                                    className="flex items-center justify-center gap-2 p-3 rounded-xl border border-slate-200 dark:border-slate-800 dark:text-slate-300 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all font-medium text-slate-700 text-sm relative"
                                >
                                    <span className="text-blue-500 font-bold">Th</span>
                                    Things 3
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* Todoist */}
                                <button
                                    onClick={() => shareToApp('todoist', false)}
                                    disabled={sharingTo === 'todoist'}
                                    className={`flex items-center justify-center gap-2 p-3 rounded-xl border transition-all font-medium text-slate-700 dark:text-slate-300 text-sm relative ${initialProvider === 'todoist' ? 'border-brand-blue bg-blue-50 dark:bg-blue-900/20 ring-2 ring-brand-blue/20' : 'border-slate-200 dark:border-slate-800 hover:border-red-200 dark:hover:border-red-900/40 hover:bg-red-50 dark:hover:bg-red-900/20'}`}
                                >
                                    {sharingTo === 'todoist' ? <span className="animate-spin">⏳</span> : <span className="text-red-500 font-bold">T</span>}
                                    Todoist
                                    {connectedApps.has('todoist') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                </button>
                                {/* MS To Do */}
                                <button
                                    onClick={() => shareToApp('microsoft_todo', true)}
                                    disabled={sharingTo === 'microsoft_todo'}
                                    className="flex items-center justify-center gap-2 p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-blue-200 dark:hover:border-blue-900/40 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all font-medium text-slate-700 dark:text-slate-300 text-sm relative"
                                >
                                    {sharingTo === 'microsoft_todo' ? <span className="animate-spin">⏳</span> : <span className="text-blue-600 font-bold">✓</span>}
                                    MS To Do
                                    {connectedApps.has('microsoft_todo') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                                {/* TickTick */}
                                <button
                                    onClick={() => shareToApp('ticktick', true)}
                                    disabled={sharingTo === 'ticktick'}
                                    className="flex items-center justify-center gap-2 p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-blue-200 dark:hover:border-blue-900/40 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all font-medium text-slate-700 dark:text-slate-300 text-sm relative"
                                >
                                    {sharingTo === 'ticktick' ? <span className="animate-spin">⏳</span> : <span className="text-blue-400 font-bold">✔</span>}
                                    TickTick
                                    {connectedApps.has('ticktick') && <Check size={14} className="absolute top-2 right-2 text-green-500" />}
                                    {!isPro && <Lock size={12} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />}
                                </button>
                            </div>
                        </div>

                        {/* Storage & Communication */}
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                                <Cloud size={12} /> Storage & Communication
                            </h4>
                            <div className="grid grid-cols-3 gap-3">
                                <button onClick={() => shareToApp('google_drive', true)} className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors relative border border-slate-100 dark:border-slate-800">
                                    <Database size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Drive</span>
                                    {connectedApps.has('google_drive') && <Check size={12} className="absolute top-1 right-1 text-green-500" />}
                                    {!isPro && <Lock size={10} className="absolute top-1 right-1 text-slate-300 dark:text-slate-600" />}
                                </button>
                                <button onClick={() => shareToApp('dropbox', true)} className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors relative border border-slate-100 dark:border-slate-800">
                                    <Database size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Dropbox</span>
                                    {connectedApps.has('dropbox') && <Check size={12} className="absolute top-1 right-1 text-green-500" />}
                                    {!isPro && <Lock size={10} className="absolute top-1 right-1 text-slate-300 dark:text-slate-600" />}
                                </button>
                                <button onClick={() => shareToApp('google_calendar', true)} className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors relative border border-slate-100 dark:border-slate-800">
                                    <Calendar size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">G.Cal</span>
                                    {connectedApps.has('google_calendar') && <Check size={12} className="absolute top-1 right-1 text-green-500" />}
                                    {!isPro && <Lock size={10} className="absolute top-1 right-1 text-slate-300 dark:text-slate-600" />}
                                </button>
                                <button
                                    onClick={() => shareToApp('slack', true)}
                                    className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-colors relative border ${initialProvider === 'slack' ? 'border-brand-blue bg-blue-50 dark:bg-blue-900/20 ring-2 ring-brand-blue/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800 border-slate-100 dark:border-slate-800'}`}
                                >
                                    <MessageSquare size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Slack</span>
                                    {connectedApps.has('slack') && <Check size={12} className="absolute top-1 right-1 text-green-500" />}
                                    {!isPro && <Lock size={10} className="absolute top-1 right-1 text-slate-300 dark:text-slate-600" />}
                                </button>
                                <button onClick={downloadICS} className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors border border-slate-100 dark:border-slate-800">
                                    <Calendar size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">ICS</span>
                                </button>
                                <button onClick={sendEmail} className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors border border-slate-100 dark:border-slate-800">
                                    <Mail size={20} className="text-slate-400 dark:text-slate-500" />
                                    <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Email</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <AnimatePresence>
                        {successMsg && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="absolute bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-full shadow-lg flex items-center gap-2 z-20"
                            >
                                <Check size={16} className="text-green-400" /> {successMsg}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}
