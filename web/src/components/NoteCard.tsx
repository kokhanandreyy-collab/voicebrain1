import { useState, useRef, useEffect } from 'react';
import { Card } from './ui';
import { Note } from '../types';
import { Tag, Sparkles, Share2, Trash2, LayoutGrid, FileText, MessageSquare, Calendar, Check, Plug, Database, Mail, AlertTriangle } from 'lucide-react';
import { WaveformPlayer } from './WaveformPlayer';
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion';

interface NoteCardProps {
    note: Note;
    onEdit: (note: Note) => void;
    onDelete: (id: string) => void;
    onShare: (note: Note, provider?: string) => void;
    onStatusBadge: (note: Note) => React.ReactNode;
    selectable?: boolean;
    selected?: boolean;
    onSelect?: () => void;
}

export function NoteCard({ note, onEdit, onDelete, onShare, onStatusBadge, selectable, selected, onSelect }: NoteCardProps) {
    const [isTranscriptView, setIsTranscriptView] = useState(false);
    const x = useMotionValue(0);

    // Transform values for visual feedback
    const shareOpacity = useTransform(x, [0, 80], [0, 1]);
    const shareScale = useTransform(x, [0, 80], [0.5, 1.2]);
    const deleteOpacity = useTransform(x, [0, -80], [0, 1]);
    const deleteScale = useTransform(x, [0, -80], [0.5, 1.2]);

    const hasVibratedRight = useRef(false);
    const hasVibratedLeft = useRef(false);

    // Haptic feedback logic
    useEffect(() => {
        return x.on("change", (latest) => {
            if (latest > 80 && !hasVibratedRight.current) {
                if (navigator.vibrate) navigator.vibrate(10);
                hasVibratedRight.current = true;
            } else if (latest <= 80) {
                hasVibratedRight.current = false;
            }

            if (latest < -80 && !hasVibratedLeft.current) {
                if (navigator.vibrate) navigator.vibrate(10);
                hasVibratedLeft.current = true;
            } else if (latest >= -80) {
                hasVibratedLeft.current = false;
            }
        });
    }, [x]);

    const handleDragEnd = (_: any, info: PanInfo) => {
        if (info.offset.x > 80) {
            onShare(note);
        } else if (info.offset.x < -80) {
            onDelete(note.id);
        }
    };

    const toggleView = (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsTranscriptView(!isTranscriptView);
    };

    return (
        <div className={`relative overflow-hidden rounded-xl transition-all ${selected ? 'ring-2 ring-brand-blue ring-offset-2 dark:ring-offset-slate-950' : ''}`}>
            {selectable && (
                <div
                    className="absolute top-4 left-4 z-50 cursor-pointer"
                    onClick={(e) => { e.stopPropagation(); onSelect && onSelect(); }}
                >
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${selected ? 'bg-brand-blue border-brand-blue' : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600'}`}>
                        {selected && <Check size={14} className="text-white" />}
                    </div>
                </div>
            )}
            {/* Background Layer (Revealed on Swipe) */}
            <div className="absolute inset-0 flex items-center justify-between px-8 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl">
                {/* Share Action (revealed on right swipe) */}
                <motion.div
                    style={{ opacity: shareOpacity, scale: shareScale }}
                    className="flex flex-col items-center gap-1 text-brand-blue"
                >
                    <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                        <Share2 size={20} />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider">Quick Share</span>
                </motion.div>

                {/* Delete Action (revealed on left swipe) */}
                <motion.div
                    style={{ opacity: deleteOpacity, scale: deleteScale }}
                    className="flex flex-col items-center gap-1 text-red-500"
                >
                    <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                        <Trash2 size={20} />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider">Delete</span>
                </motion.div>
            </div>

            {/* Main Interactive Layer */}
            <motion.div
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragSnapToOrigin
                onDragEnd={handleDragEnd}
                style={{ x }}
                className="relative z-10 touch-pan-y"
            >
                <Card
                    className="group hover:shadow-md transition-all cursor-pointer border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
                    onClick={() => onEdit(note)}
                >
                    <div className="p-5">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 space-y-2">
                                <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-brand-blue transition-colors">
                                        {note.title || "Untitled Note"}
                                    </h3>
                                    {note.status === 'COMPLETED' ? (
                                        <div className="flex items-center gap-2">
                                            <div className="px-2.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-full text-xs font-medium flex items-center gap-1">
                                                <Sparkles size={10} className="text-brand-blue" />
                                                {note.mood || "Neutral"}
                                            </div>
                                            <button
                                                onClick={toggleView}
                                                className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                            >
                                                {isTranscriptView ? "Show Summary" : "Show Transcript"}
                                            </button>
                                        </div>
                                    ) : (
                                        onStatusBadge(note)
                                    )}
                                </div>
                            </div>

                            <div className="flex flex-col items-end gap-2">
                                <span className="text-xs text-slate-400 font-medium">
                                    {new Date(note.created_at).toLocaleDateString()}
                                </span>
                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity md:flex hidden">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onShare(note); }}
                                        className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                                    >
                                        <Share2 size={16} />
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onDelete(note.id); }}
                                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Progressive Rendering for Transcript */}
                        {(note.status === 'PROCESSING' || note.status === 'PENDING') && note.transcription_text && (
                            <div className="mt-4 p-4 bg-slate-50/50 dark:bg-slate-800/30 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
                                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                    Live Transcript Preview
                                </p>
                                <div className="text-slate-500 text-sm leading-relaxed italic">
                                    {note.transcription_text}...
                                </div>
                            </div>
                        )}

                        {/* Waveform Player */}
                        {note.status === 'COMPLETED' && note.audio_url && (
                            <div className="mt-4">
                                <WaveformPlayer audioUrl={note.audio_url} />
                            </div>
                        )}

                        {note.status === 'COMPLETED' && (
                            <div className="mt-4 text-slate-600 dark:text-slate-400 text-sm leading-relaxed line-clamp-3">
                                {isTranscriptView ? note.transcription_text : (note.summary || note.transcription_text)}
                            </div>
                        )}

                        {note.status === 'COMPLETED' && note.integration_status && note.integration_status.length > 0 && (
                            <div className="mt-4 flex flex-wrap gap-2">
                                {note.integration_status.map((is, idx) => (
                                    <div
                                        key={idx}
                                        className={`flex items-center gap-1.5 px-2 py-1 rounded-md border transition-colors relative group ${is.status === 'FAILED'
                                            ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                                            : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                            }`}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onShare(note, is.provider);
                                        }}
                                        title={is.error || `${is.provider}: ${is.status}`}
                                    >
                                        <span className={is.status === 'FAILED' ? 'text-red-500' : 'text-slate-400'}>
                                            {(() => {
                                                switch (is.provider) {
                                                    case 'notion': return <FileText size={12} />;
                                                    case 'slack': return <MessageSquare size={12} />;
                                                    case 'todoist': return <Check size={12} />;
                                                    case 'google_calendar': return <Calendar size={12} />;
                                                    case 'google_drive':
                                                    case 'dropbox': return <Database size={12} />;
                                                    case 'email': return <Mail size={12} />;
                                                    default: return <Plug size={12} />;
                                                }
                                            })()}
                                        </span>

                                        {is.status === 'FAILED' ? (
                                            <div className="text-red-500">
                                                <AlertTriangle size={10} />
                                            </div>
                                        ) : (
                                            <div className={`w-1.5 h-1.5 rounded-full ${is.status === 'SUCCESS' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                                        )}

                                        {is.status === 'FAILED' && is.error && (
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-white text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg">
                                                {is.error}
                                                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex flex-wrap gap-2 pt-4">
                            {/* Topic Badge */}
                            {(note as any).cluster_id && (
                                <span className="flex items-center gap-1 text-[10px] font-bold text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/30 border border-violet-100 dark:border-violet-800 px-2 py-1 rounded-full uppercase tracking-wider">
                                    <LayoutGrid size={10} /> {(note as any).cluster_id.replace('topic_', 'Topic ')}
                                </span>
                            )}

                            {(note.tags || []).map(tag => (
                                <span key={tag} className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-md">
                                    <Tag size={10} /> {tag}
                                </span>
                            ))}
                        </div>

                        {/* Diarization Display (Mini) */}
                        {(note as any).diarization && (note as any).diarization.length > 0 && isTranscriptView && (
                            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 space-y-2">
                                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-2">Speakers Detected</p>
                                <div className="space-y-3">
                                    {((note as any).diarization as any[]).map((turn: any, i: number) => (
                                        <div key={i} className="flex gap-3 text-sm">
                                            <div className="min-w-[60px] text-xs font-bold text-slate-500 uppercase pt-1">
                                                {turn.speaker}
                                            </div>
                                            <div className="text-slate-700 dark:text-slate-300 leading-relaxed">
                                                {turn.text}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </Card>
            </motion.div>
        </div>
    );
}
