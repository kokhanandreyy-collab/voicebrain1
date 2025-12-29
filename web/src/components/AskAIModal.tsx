import { Fragment, useState, useEffect, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Sparkles, X, Send, BrainCircuit, Bot, Mic, Trash2 } from 'lucide-react';
// import { Button } from './ui';
import api from '../api';
import ReactMarkdown from 'react-markdown';

interface AskAIModalProps {
    isOpen: boolean;
    onClose: () => void;
    initialQuery?: string;
    autoStartListening?: boolean;
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export function AskAIModal({ isOpen, onClose, initialQuery = '', autoStartListening = false }: AskAIModalProps) {
    const [query, setQuery] = useState(initialQuery);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Voice State
    const [isVoiceRecording, setIsVoiceRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    // ... startVoiceInput implementation ...

    useEffect(() => {
        if (isOpen) {
            if (initialQuery) {
                setQuery(initialQuery);
                handleAsk(initialQuery);
            } else {
                setMessages([]);
                setQuery('');
                if (autoStartListening) {
                    // Slight delay to ensure UI is ready
                    setTimeout(() => startVoiceInput(), 500);
                }
            }
        } else {
            stopVoiceInput(); // Ensure recording stops if modal closes
        }
    }, [isOpen, initialQuery, autoStartListening]);

    const startVoiceInput = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());

                // Send for transcription
                try {
                    setQuery("Listening... Processing...");
                    const formData = new FormData();
                    formData.append('file', blob, 'voice_query.webm');
                    const { data } = await api.post('/notes/transcribe', formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                    setQuery(data.text);
                } catch (error) {
                    console.error("Transcription failed", error);
                    setQuery("");
                    alert("Could not transcribe voice.");
                } finally {
                    setIsVoiceRecording(false);
                }
            };

            mediaRecorder.start();
            setIsVoiceRecording(true);
        } catch (err) {
            console.error("Mic error", err);
            alert("Microphone access denied");
        }
    };

    const stopVoiceInput = () => {
        if (mediaRecorderRef.current && isVoiceRecording) {
            mediaRecorderRef.current.stop();
        }
    };

    useEffect(() => {
        if (isOpen && initialQuery) {
            setQuery(initialQuery);
            handleAsk(initialQuery);
        } else if (isOpen) {
            setMessages([]); // Reset on open if no initial query
            setQuery('');
        }
    }, [isOpen, initialQuery]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleAsk = async (q: string) => {
        if (!q.trim()) return;

        // Add User Message
        const userMsg: Message = { role: 'user', content: q };
        setMessages(prev => [...prev, userMsg]);
        setQuery('');
        setIsLoading(true);

        try {
            const { data } = await api.post('/notes/ask', { question: q });
            const aiMsg: Message = { role: 'assistant', content: data.answer };
            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            console.error("Ask AI Failed", error);
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error appearing into your brain." }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={onClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4 text-center">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white dark:bg-slate-900 p-0 text-left align-middle shadow-2xl transition-all border border-slate-100 dark:border-slate-800 flex flex-col h-[600px]">
                                {/* Header */}
                                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
                                    <div className="flex items-center gap-2">
                                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-purple-500/20">
                                            <BrainCircuit size={18} />
                                        </div>
                                        <div>
                                            <Dialog.Title as="h3" className="text-lg font-bold text-slate-900 dark:text-white leading-tight">
                                                Ask Your Brain
                                            </Dialog.Title>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Powered by RAG & DeepSeek V3</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => setMessages([])}
                                            className="text-slate-400 hover:text-red-500 transition-colors p-1.5 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-full"
                                            title="Clear Context"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                        <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1" />
                                        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full">
                                            <X size={20} />
                                        </button>
                                    </div>
                                </div>

                                {/* Chat Area */}
                                <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30 dark:bg-slate-950/30">
                                    {messages.length === 0 && !isLoading && (
                                        <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-50">
                                            <Sparkles size={48} className="text-brand-blue" />
                                            <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs">Ask anything about your notes. "What did I say about the project deadline?"</p>
                                        </div>
                                    )}

                                    {messages.map((msg, idx) => (
                                        <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-slate-200 dark:bg-slate-800' : 'bg-brand-blue text-white'}`}>
                                                {msg.role === 'user' ? <div className="w-4 h-4 bg-slate-500 dark:bg-slate-400 rounded-full" /> : <Bot size={16} />}
                                            </div>
                                            <div className={`rounded-2xl p-4 max-w-[80%] text-sm leading-relaxed shadow-sm ${msg.role === 'user'
                                                ? 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-slate-700 rounded-tr-none'
                                                : 'bg-white dark:bg-slate-950 text-slate-700 dark:text-slate-300 border border-slate-100 dark:border-slate-800 rounded-tl-none'
                                                }`}>
                                                <ReactMarkdown className="prose prose-sm prose-slate dark:prose-invert max-w-none">
                                                    {msg.content}
                                                </ReactMarkdown>
                                            </div>
                                        </div>
                                    ))}

                                    {isLoading && (
                                        <div className="flex gap-4">
                                            <div className="w-8 h-8 rounded-full bg-brand-blue text-white flex items-center justify-center shrink-0 animate-pulse">
                                                <Bot size={16} />
                                            </div>
                                            <div className="bg-white dark:bg-slate-950 px-4 py-3 rounded-2xl rounded-tl-none border border-slate-100 dark:border-slate-800 shadow-sm flex items-center gap-2">
                                                <span className="w-2 h-2 bg-brand-blue rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                                <span className="w-2 h-2 bg-brand-blue rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                                <span className="w-2 h-2 bg-brand-blue rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                            </div>
                                        </div>
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>

                                {/* Input Area */}
                                <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
                                    <form
                                        onSubmit={(e) => {
                                            e.preventDefault();
                                            handleAsk(query);
                                        }}
                                        className="relative flex items-center"
                                    >
                                        <div className="relative w-full">
                                            <input
                                                type="text"
                                                value={query}
                                                onChange={(e) => setQuery(e.target.value)}
                                                placeholder={isVoiceRecording ? "Listening..." : "Ask a question..."}
                                                className={`w-full pl-5 pr-20 py-3.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue transition-all dark:text-white ${isVoiceRecording ? 'placeholder:text-brand-blue animate-pulse border-brand-blue/50' : ''}`}
                                                disabled={isLoading || isVoiceRecording}
                                            />
                                            {/* Voice Button */}
                                            <button
                                                type="button"
                                                onClick={isVoiceRecording ? stopVoiceInput : startVoiceInput}
                                                className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors ${isVoiceRecording ? 'bg-red-50 dark:bg-red-900/30 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50' : 'text-slate-400 hover:text-brand-blue hover:bg-slate-100 dark:hover:bg-slate-800'}`}
                                                title="Voice Input"
                                            >
                                                {isVoiceRecording ? <div className="w-4 h-4 bg-red-500 rounded-sm animate-pulse" /> : <Mic size={18} />}
                                            </button>
                                        </div>
                                        <button
                                            type="submit"
                                            disabled={!query.trim() || isLoading || isVoiceRecording}
                                            className="ml-2 p-3 bg-brand-blue text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:hover:bg-brand-blue transition-colors shadow-sm shrink-0"
                                        >
                                            <Send size={18} />
                                        </button>
                                    </form>
                                    <p className="text-[10px] text-center text-slate-400 mt-2">AI can make mistakes. Verify important info.</p>
                                </div>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
}
