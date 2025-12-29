import { useEffect, useRef, useState, useMemo } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';
import { cn } from './ui';
import { useTheme } from '../context/ThemeContext';

interface WaveformPlayerProps {
    audioUrl: string;
    height?: number;
    className?: string;
}

export function WaveformPlayer({ audioUrl, height = 40, className }: WaveformPlayerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const wavesurferRef = useRef<WaveSurfer | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const { theme } = useTheme();

    const effectiveTheme = useMemo(() => {
        if (theme === 'system') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return theme;
    }, [theme]);

    useEffect(() => {
        if (!containerRef.current) return;

        const ws = WaveSurfer.create({
            container: containerRef.current,
            waveColor: effectiveTheme === 'dark' ? '#334155' : '#E2E8F0', // slate-700 : slate-200
            progressColor: '#2563EB', // brand-blue
            cursorColor: '#2563EB',
            barWidth: 2,
            barRadius: 3,
            height: height,
            normalize: true
        });

        ws.load(audioUrl);

        ws.on('play', () => setIsPlaying(true));
        ws.on('pause', () => setIsPlaying(false));
        ws.on('ready', () => setDuration(ws.getDuration()));
        ws.on('audioprocess', () => setCurrentTime(ws.getCurrentTime()));
        ws.on('interaction', () => setCurrentTime(ws.getCurrentTime()));

        wavesurferRef.current = ws;

        return () => {
            ws.destroy();
        };
    }, [audioUrl, height, effectiveTheme]);

    const togglePlay = (e: React.MouseEvent) => {
        e.stopPropagation();
        wavesurferRef.current?.playPause();
    };

    const toggleMute = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (wavesurferRef.current) {
            const newMute = !isMuted;
            wavesurferRef.current.setMuted(newMute);
            setIsMuted(newMute);
        }
    };

    const formatTime = (time: number) => {
        const minutes = Math.floor(time / 60);
        const seconds = Math.floor(time % 60);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    return (
        <div
            className={cn(
                "flex items-center gap-3 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl p-3 shadow-sm hover:shadow-md transition-shadow",
                className
            )}
            onClick={(e) => e.stopPropagation()}
        >
            <button
                onClick={togglePlay}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-brand-blue text-white shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
            >
                {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
            </button>

            <div className="flex-1 flex flex-col gap-1">
                <div ref={containerRef} className="w-full" />
                <div className="flex justify-between items-center px-1">
                    <span className="text-[10px] font-mono text-slate-400 font-bold">
                        {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                    <button
                        onClick={toggleMute}
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                    >
                        {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                    </button>
                </div>
            </div>
        </div>
    );
}
