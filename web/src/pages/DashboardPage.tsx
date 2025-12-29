import { useEffect, useState, useRef } from 'react';
import api from '../api';
import { Note } from '../types';
import { Button } from '../components/ui';
import AudioRecorder from '../components/AudioRecorder';
import { Mic, Sparkles, Folder, Star, Loader2, Settings, LogOut, Bug, BarChart3, Trash2, Download, X, CheckSquare } from 'lucide-react';
import { AnimatePresence } from 'framer-motion';
import { FeedbackModal } from '../components/FeedbackModal';
import { savePendingUpload, getPendingUploads, deletePendingUpload } from '../lib/storage';
import { EditNoteModal } from '../components/EditNoteModal';
import { ShareModal } from '../components/ShareModal';
import { SearchInput } from '../components/SearchInput';
import { AskAIModal } from '../components/AskAIModal';
import { NoteCard } from '../components/NoteCard';
import { EmptyState } from '../components/EmptyState';
import { OnboardingModal } from '../components/OnboardingModal';
// import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';


export default function DashboardPage() {
    const [notes, setNotes] = useState<Note[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [_isSyncing, setIsSyncing] = useState(false);
    const [processingStep, setProcessingStep] = useState<string>(''); // For "Optimizing..." vs "Transcribing..."
    const [uploadProgress, setUploadProgress] = useState(0);
    const [isOnline, setIsOnline] = useState(navigator.onLine);

    // User State for Tariffs
    const [user, setUser] = useState<any>(null);

    // Search State
    const [searchQuery, setSearchQuery] = useState('');
    const [isVoiceSearching, setIsVoiceSearching] = useState(false);
    const [isAskAIOpen, setIsAskAIOpen] = useState(false);
    const [isAskAIAutoStart, setIsAskAIAutoStart] = useState(false);
    const searchMediaRecorder = useRef<MediaRecorder | null>(null);
    const audioRecorderRef = useRef<any>(null);

    // Modal State
    const [sharingNote, setSharingNote] = useState<Note | null>(null);
    const [sharingProvider, setSharingProvider] = useState<string | undefined>();
    const [editingNote, setEditingNote] = useState<Note | null>(null);
    const [viewingFeedback, setViewingFeedback] = useState(false);

    // Bulk Mode
    const [isSelectionMode, setIsSelectionMode] = useState(false);
    const [selectedNoteIds, setSelectedNoteIds] = useState<string[]>([]);

    const fetchNotes = async (query = '', silent = false) => {
        try {
            const endpoint = query ? `/notes?q=${encodeURIComponent(query)}` : '/notes';
            const { data } = await api.get(endpoint);
            setNotes(data);
        } catch (error) {
            if (!silent) console.error(error);
        }
    };

    const fetchUser = async () => {
        try {
            const { data } = await api.get('/auth/me');
            setUser(data);
        } catch (e) {
            console.error(e);
        }
    };

    const uploadAudio = async (blob: Blob) => {
        setProcessingStep('Загрузка транскрипции...');
        setUploadProgress(0);
        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');
        await api.post('/notes/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.total) {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    setUploadProgress(percentCompleted);
                }
            }
        });
    };

    const syncPending = async () => {
        if (!navigator.onLine) return;

        try {
            const pending = await getPendingUploads();
            if (pending.length === 0) return;

            setIsSyncing(true);

            for (const item of pending) {
                try {
                    await uploadAudio(item.blob);
                    await deletePendingUpload(item.id);
                } catch (err) {
                    console.error("Failed to sync item", item.id, err);
                }
            }
            await fetchNotes();
            fetchUser();
        } catch (error) {
            console.error("Sync error:", error);
        } finally {
            setIsSyncing(false);
        }
    };

    const handleRecordingComplete = async (audioBlob: Blob) => {
        if (!navigator.onLine) {
            try {
                await savePendingUpload(audioBlob);
                alert("You are offline. Recording saved locally and will sync when online.");
            } catch (err) {
                alert("Failed to save offline recording.");
            }
            return;
        }

        setIsProcessing(true);
        try {
            await uploadAudio(audioBlob);
            await fetchNotes();
            await fetchUser();
        } catch (error: any) {
            console.error("Upload/Processing failed:", error);
            if (error.response?.status === 403) {
                alert(error.response.data.detail || "Limit reached. Please upgrade to Pro.");
            } else {
                console.error("Upload failed, saving locally:", error);
                try {
                    await savePendingUpload(audioBlob);
                    alert("Upload failed (Network/Error). Saved locally for retry.");
                } catch (e) {
                    alert("Critial error: could not save recording.");
                }
            }
        } finally {
            setIsProcessing(false);
            setProcessingStep('');
            setUploadProgress(0);
        }
    };

    const handleDelete = async (noteId: string) => {
        if (!confirm("Are you sure you want to delete this note? This cannot be undone.")) return;
        try {
            await api.delete(`/notes/${noteId}`);
            setNotes(notes.filter(n => n.id !== noteId));
        } catch (error) {
            alert("Failed to delete note");
        }
    };

    const startVoiceSearch = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            searchMediaRecorder.current = mediaRecorder;
            const chunks: Blob[] = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());

                setSearchQuery("Listening...");

                try {
                    const formData = new FormData();
                    formData.append('file', blob, 'search.webm');
                    const { data } = await api.post('/notes/search/voice', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    setNotes(data);
                    setSearchQuery("");
                } catch (error) {
                    console.error("Voice search failed", error);
                    setSearchQuery("");
                    alert("Voice search failed");
                } finally {
                    setIsVoiceSearching(false);
                }
            };

            mediaRecorder.start();
            setIsVoiceSearching(true);

            setTimeout(() => {
                if (mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                }
            }, 4000);

        } catch (err) {
            console.error("Mic error", err);
            alert("Could not access microphone");
        }
    };

    const stopVoiceSearch = () => {
        if (searchMediaRecorder.current && searchMediaRecorder.current.state === 'recording') {
            searchMediaRecorder.current.stop();
        }
    };


    const StatusBadge = ({ note }: { note: Note }) => {
        const { status, processing_step } = note;
        if (status === 'COMPLETED') return null;
        if (status === 'FAILED') return <span className="text-xs text-red-500 font-bold">FAILED</span>;
        return (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-brand-blue rounded-full text-xs font-bold animate-pulse border border-blue-100 shadow-sm">
                <Loader2 size={12} className="animate-spin" />
                <span>{processing_step || status}</span>
            </div>
        );
    };

    // Effects
    useEffect(() => {
        const hasProcessing = notes.some(n => n.status === 'PENDING' || n.status === 'PROCESSING');
        if (!hasProcessing) return;

        // Visibility Check
        if (document.hidden) return;

        let intervalId: NodeJS.Timeout;
        let delay = 3000;

        // Polling function with dynamic delay (simple implementation with fixed interval here for simplicity in useEffect but requesting backoff logic)
        // Since setInterval doesn't support changing delay easily, we use recursive setTimeout for backoff
        // However, the user asked for *exponential backoff* if status doesn't change.
        // We'll reset delay on any status change.

        // Actually, simpler approach for component:
        // 1. If processing, poll. 2. If tab hidden, stop.
        // 3. For backoff, we need state. simpler is just 3s interval.
        // BUT strict constraint: "Implement exponential backoff... if status doesn't change".

        const poll = async () => {
            if (document.hidden) return;

            try {
                const endpoint = searchQuery ? `/notes?q=${encodeURIComponent(searchQuery)}` : '/notes';
                const { data } = await api.get(endpoint);

                // Check if any change in STATUS
                const prevStatuses = notes.map(n => n.status).join(',');
                const newStatuses = (data as Note[]).map(n => n.status).join(',');

                if (prevStatuses !== newStatuses) {
                    setNotes(data);
                    delay = 3000; // Reset to fast poll on progress
                } else {
                    delay = Math.min(delay * 1.5, 30000); // Backoff
                }

                // Re-schedule
                if (data.some((n: Note) => n.status === 'PENDING' || n.status === 'PROCESSING')) {
                    intervalId = setTimeout(poll, delay);
                }
            } catch (e) {
                console.error(e);
                delay = 30000; // Slow down on error
                intervalId = setTimeout(poll, delay);
            }
        };

        intervalId = setTimeout(poll, 3000);

        return () => clearTimeout(intervalId);
    }, [notes, searchQuery]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (!isVoiceSearching) {
                fetchNotes(searchQuery);
            }
        }, 500);
        return () => clearTimeout(timer);
    }, [searchQuery, isVoiceSearching]);

    useEffect(() => {
        fetchUser();
        fetchNotes();

        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            localStorage.setItem('token', token);
            window.history.replaceState({}, document.title, window.location.pathname);
        }

        const handleOnline = () => {
            setIsOnline(true);
            syncPending();
        };
        const handleOffline = () => setIsOnline(false);

        const handleRemoteRecord = () => {
            if (audioRecorderRef.current) {
                audioRecorderRef.current.startRecording();
            }
        };

        window.addEventListener('start-recording', handleRemoteRecord);
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // Electron Integration
        if (window.electronAPI) {
            window.electronAPI.onStartRecording(handleRemoteRecord);
        }

        syncPending();

        // Push Notifications
        const subscribePush = async () => {
            if ('serviceWorker' in navigator && 'PushManager' in window) {
                try {
                    const reg = await navigator.serviceWorker.register('/sw.js');
                    await navigator.serviceWorker.ready;

                    if (Notification.permission === 'default') {
                        await Notification.requestPermission();
                    }

                    if (Notification.permission === 'granted') {
                        const vapidKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
                        if (!vapidKey) {
                            console.warn("VITE_VAPID_PUBLIC_KEY not found");
                            return;
                        }

                        const sub = await reg.pushManager.subscribe({
                            userVisibleOnly: true,
                            applicationServerKey: urlBase64ToUint8Array(vapidKey)
                        });

                        await api.post('/notifications/subscribe', sub);
                        console.log("Push Subscribed");
                    }
                } catch (e) {
                    console.error("Push subscription error", e);
                }
            }
        };
        subscribePush();

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
            window.removeEventListener('start-recording', handleRemoteRecord);
        };
    }, []);

    const getResetDate = (currentUser: any) => {
        if (!currentUser) return '';
        const now = new Date();

        if (currentUser.tier === 'free' || !currentUser.tier) {
            // Free: Resets 1st of next month
            const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
            return nextMonth.toLocaleDateString();
        } else if (currentUser.billing_cycle_start) {
            // Paid: 30 days from billing start
            const start = new Date(currentUser.billing_cycle_start);
            const reset = new Date(start);
            reset.setDate(start.getDate() + 30);
            return reset.toLocaleDateString();
        }
        return 'Unknown';
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
            <div className="bg-noise" />

            <EditNoteModal
                isOpen={!!editingNote}
                onClose={() => setEditingNote(null)}
                note={editingNote}
                onSave={(updated) => {
                    setNotes(notes.map(n => n.id === updated.id ? updated : n));
                }}
                onSelectRelated={(relatedId) => {
                    const related = notes.find(n => n.id === relatedId);
                    if (related) {
                        setEditingNote(related);
                    } else {
                        // Optional: Fetch if not in current list (though we fetch all currently)
                        // For now we assume typical user library fits or we handle this later
                        console.warn("Related note not in current view list", relatedId);
                    }
                }}
            />

            {/* Modals */}
            {user && !user.has_onboarded && (
                <OnboardingModal
                    isOpen={true}
                    onComplete={(updatedUser) => setUser(updatedUser)}
                />
            )}

            <ShareModal
                isOpen={!!sharingNote}
                onClose={() => { setSharingNote(null); setSharingProvider(undefined); }}
                note={sharingNote}
                initialProvider={sharingProvider}
            />

            <AskAIModal
                isOpen={isAskAIOpen}
                onClose={() => setIsAskAIOpen(false)}
                autoStartListening={isAskAIAutoStart}
            />

            <nav className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg border-b border-slate-200 dark:border-slate-800">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-brand-blue rounded-lg flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                            <Mic size={18} />
                        </div>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">VoiceBrain</h1>
                    </div>
                    <div className="flex items-center gap-4">
                        {!isOnline && <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full font-medium">Offline Mode</span>}

                        {user && !user.is_pro && (
                            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-full border border-slate-200 dark:border-slate-700" title={`Free Plan Usage (Resets: ${getResetDate(user)})`}>
                                <div className="w-20 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${((user.seconds_used_this_month || 0) / 7200) > 0.9 ? 'bg-red-500' : 'bg-brand-blue'}`}
                                        style={{ width: `${Math.min(100, ((user.seconds_used_this_month || 0) / 7200) * 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                                    {Math.round((user.seconds_used_this_month || 0) / 60)}/120m
                                </span>
                            </div>
                        )}
                        {user && user.is_pro && (user.tier === 'premium' ? (
                            <span className="hidden sm:inline-flex items-center gap-1 px-3 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-full border border-purple-100 dark:border-purple-800 text-xs font-bold uppercase tracking-wide">
                                <Sparkles size={12} /> PREMIUM UNLIMITED
                            </span>
                        ) : (
                            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 rounded-full border border-blue-100 dark:border-blue-800" title={`Pro Usage (Resets: ${getResetDate(user)})`}>
                                <div className="w-20 h-2 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full bg-brand-blue`}
                                        style={{ width: `${Math.min(100, ((user.seconds_used_this_month || 0) / 72000) * 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs font-bold text-brand-blue dark:text-blue-400">
                                    {Math.round((user.seconds_used_this_month || 0) / 60)}/1200m
                                </span>
                            </div>
                        ))}

                        <Link to="/stats" className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors" title="Stats & Profile">
                            <BarChart3 size={20} />
                        </Link>

                        <Link to="/settings" className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors" title="Settings">
                            <Settings size={20} />
                        </Link>

                        <button
                            onClick={() => setViewingFeedback(true)}
                            className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
                            title="Feedback / Bug Report"
                        >
                            <Bug size={20} />
                        </button>

                        <Button variant="ghost" size="sm" onClick={() => {
                            localStorage.removeItem('token');
                            window.location.href = '/login';
                        }}>
                            <LogOut size={16} className="hidden sm:inline mr-2" /> Log Out
                        </Button>
                        <div className="flex items-center gap-3 pl-2 border-l border-slate-200 dark:border-slate-800">
                            {user?.streak_days > 0 && (
                                <div className="group relative flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-500 rounded-full cursor-help transition-all hover:scale-105 border border-orange-100 dark:border-orange-900/50">
                                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-48 bg-slate-900 text-white text-xs p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-xl z-50 text-center">
                                        🔥 {user.streak_days} day streak! Record a note tomorrow to keep it burning!
                                    </div>
                                    <span className="text-lg">🔥</span>
                                    <span className="font-bold text-sm font-mono">{user.streak_days}</span>
                                </div>
                            )}
                            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 flex items-center justify-center font-bold text-slate-500 text-xs">
                                {user?.full_name?.substring(0, 2).toUpperCase() || 'VB'}
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <div className="max-w-5xl mx-auto p-6 space-y-12">
                <section className="py-8 bg-white dark:bg-slate-900 rounded-[2rem] border border-slate-100 dark:border-slate-800 shadow-soft flex flex-col items-center justify-center space-y-6 mt-8">
                    <div className="text-center space-y-1">
                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">New Note</h2>
                        <p className="text-slate-400 dark:text-slate-500">Capture your ideas instantly</p>
                    </div>
                    <AudioRecorder
                        ref={audioRecorderRef}
                        onRecordingComplete={handleRecordingComplete}
                        isProcessing={isProcessing}
                        processingStep={processingStep}
                        uploadProgress={uploadProgress}
                    />

                    {user && !user.is_pro && (user.seconds_used_this_month || 0) >= 7200 && (
                        <p className="text-red-500 text-sm font-medium animate-pulse text-center">
                            Wait! You've reached your monthly limit (120 min). <Link to="/pricing" className="underline font-bold hover:text-red-600">Upgrade to Pro</Link> for 1200 minutes!
                        </p>
                    )}
                    {user && user.tier === 'pro' && (user.seconds_used_this_month || 0) >= 72000 && (
                        <p className="text-red-500 text-sm font-medium animate-pulse text-center">
                            Pro limit reached (1200 minutes). <Link to="/pricing" className="underline font-bold hover:text-red-600">Upgrade to Premium</Link> for Unlimited.
                        </p>
                    )}
                </section>

                <div className="flex gap-8">
                    <aside className="hidden md:block w-64 space-y-6">
                        <div className="space-y-2">
                            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider pl-3 mb-2">Library</p>
                            <button onClick={() => { setSearchQuery(''); fetchNotes(); }} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/40 text-brand-blue dark:text-blue-400 font-medium">
                                <Folder size={18} /> All Notes
                            </button>
                            <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium transition-colors">
                                <Star size={18} /> Favorites
                            </button>
                        </div>
                    </aside>

                    <main className="flex-1 space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Recent Notes</h2>
                            <div className="w-full md:w-auto flex items-center gap-3">
                                <div className="flex items-center gap-2">
                                    <Button
                                        className="hidden md:flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white border-0 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40"
                                        onClick={() => {
                                            setIsAskAIAutoStart(false);
                                            setIsAskAIOpen(true);
                                        }}
                                    >
                                        <Sparkles size={16} /> Ask AI
                                    </Button>
                                    <button
                                        className="hidden md:flex items-center justify-center p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-brand-blue dark:text-blue-400 shadow-sm hover:border-brand-blue dark:hover:border-brand-blue hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-all"
                                        title="Voice Ask AI"
                                        onClick={() => {
                                            setIsAskAIAutoStart(true);
                                            setIsAskAIOpen(true);
                                        }}
                                    >
                                        <Mic size={18} />
                                    </button>
                                </div>
                                <SearchInput
                                    value={searchQuery}
                                    onChange={setSearchQuery}
                                    isVoiceSearching={isVoiceSearching}
                                    onStartVoice={startVoiceSearch}
                                    onStopVoice={stopVoiceSearch}
                                    className="w-full md:w-80"
                                />
                            </div>
                        </div>

                        {/* Filters & Selection Toggle */}
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-slate-500 font-medium">
                                {notes.length} notes found
                            </span>
                            <button
                                onClick={() => {
                                    setIsSelectionMode(!isSelectionMode);
                                    if (isSelectionMode) setSelectedNoteIds([]);
                                }}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold transition-all ${isSelectionMode ? 'bg-brand-blue text-white shadow-md shadow-blue-500/20' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
                            >
                                <CheckSquare size={16} />
                                {isSelectionMode ? 'Done' : 'Select'}
                            </button>
                        </div>

                        {/* Onboarding UI / Empty State */}
                        {notes.length === 0 ? (
                            <EmptyState onSelectTemplate={(t) => {
                                // Potentially fill a future transcription text box or just start mic
                                // For now, we'll just log it or maybe pass it to AudioRecorder if we update it.
                                console.log("Selecting template:", t);
                            }} />
                        ) : (
                            <div className="grid gap-4">
                                <AnimatePresence>
                                    {notes.map((note) => (
                                        <NoteCard
                                            key={note.id}
                                            note={note}
                                            onEdit={setEditingNote}
                                            onDelete={handleDelete}
                                            onShare={(n, p) => { setSharingProvider(p); setSharingNote(n); }}
                                            onStatusBadge={(n) => <StatusBadge note={n} />}
                                            selectable={isSelectionMode}
                                            selected={selectedNoteIds.includes(note.id)}
                                            onSelect={() => {
                                                if (selectedNoteIds.includes(note.id)) {
                                                    setSelectedNoteIds(selectedNoteIds.filter(id => id !== note.id));
                                                } else {
                                                    setSelectedNoteIds([...selectedNoteIds, note.id]);
                                                }
                                            }}
                                        />
                                    ))}
                                </AnimatePresence>
                            </div>
                        )}

                        {/* Floating Action Bar */}
                        <AnimatePresence>
                            {isSelectionMode && (
                                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white dark:bg-slate-800 px-6 py-3 rounded-2xl shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom-10 fade-in duration-300">
                                    <span className="text-sm font-bold bg-slate-800 dark:bg-slate-700 px-2 py-1 rounded">
                                        {selectedNoteIds.length} Selected
                                    </span>
                                    <div className="h-6 w-px bg-slate-700" />

                                    <button
                                        className="flex items-center gap-2 text-sm font-medium hover:text-red-400 transition-colors"
                                        onClick={async () => {
                                            if (!confirm(`Delete ${selectedNoteIds.length} notes?`)) return;
                                            try {
                                                await api.post('/notes/batch/delete', { note_ids: selectedNoteIds });
                                                setNotes(notes.filter(n => !selectedNoteIds.includes(n.id)));
                                                setSelectedNoteIds([]);
                                                setIsSelectionMode(false);
                                            } catch (e) { alert("Failed to delete notes"); }
                                        }}
                                    >
                                        <Trash2 size={16} /> Delete
                                    </button>

                                    <button
                                        className="flex items-center gap-2 text-sm font-medium hover:text-blue-400 transition-colors"
                                        onClick={async () => {
                                            try {
                                                const res = await api.post('/exports/batch', { note_ids: selectedNoteIds }, { responseType: 'blob' });
                                                const url = window.URL.createObjectURL(new Blob([res.data]));
                                                const link = document.createElement('a');
                                                link.href = url;
                                                link.setAttribute('download', `voicebrain_export_batch_${new Date().getTime()}.zip`);
                                                document.body.appendChild(link);
                                                link.click();
                                                link.remove();
                                                setIsSelectionMode(false);
                                                setSelectedNoteIds([]);
                                            } catch (e) { alert("Failed to export notes"); }
                                        }}
                                    >
                                        <Download size={16} /> Export
                                    </button>

                                    <div className="h-6 w-px bg-slate-700" />
                                    <button
                                        className="text-slate-400 hover:text-white"
                                        onClick={() => { setIsSelectionMode(false); setSelectedNoteIds([]); }}
                                    >
                                        <X size={18} />
                                    </button>
                                </div>
                            )}
                        </AnimatePresence>
                    </main>
                </div>
            </div>

            <FeedbackModal
                isOpen={viewingFeedback}
                onClose={() => setViewingFeedback(false)}
            />
        </div>
    );
}

function urlBase64ToUint8Array(base64String: string) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
