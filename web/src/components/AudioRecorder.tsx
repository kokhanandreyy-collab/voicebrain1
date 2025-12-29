import { useState, useRef, forwardRef, useImperativeHandle } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import { Button, cn } from './ui';
import { motion } from 'framer-motion';

interface AudioRecorderProps {
    onRecordingComplete: (audioBlob: Blob) => void;
    isProcessing: boolean;
    processingStep?: string;
    uploadProgress?: number;
}

const AudioRecorder = forwardRef((props: AudioRecorderProps, ref) => {
    const { onRecordingComplete, isProcessing, processingStep, uploadProgress } = props;
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);
    const [duration, setDuration] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    useImperativeHandle(ref, () => ({
        startRecording: () => {
            if (!isRecording && !isProcessing) {
                startRecording();
            }
        },
        stopRecording: () => {
            if (isRecording) {
                stopRecording();
            }
        }
    }));

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Determine supported mimeType for efficient/compatible recording
            let options: MediaRecorderOptions = {};
            let mimeType = '';

            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                // Safari 14.1+ supports audio/mp4 for MediaRecorder
                mimeType = 'audio/mp4';
            }

            if (mimeType) {
                options = { mimeType };
            }

            const mediaRecorder = new MediaRecorder(stream, options);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                // Use the negotiated mimeType or fallback to recorder's actual type
                const finalMimeType = mimeType || mediaRecorder.mimeType || 'audio/webm';
                const blob = new Blob(chunksRef.current, { type: finalMimeType });
                onRecordingComplete(blob);
                if (stream) stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
            setDuration(0);

            timerRef.current = setInterval(() => {
                setDuration(prev => prev + 1);
            }, 1000);
        } catch (err) {
            console.error("Mic Error:", err);
            alert("Could not access microphone.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            if (timerRef.current) clearInterval(timerRef.current);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col items-center gap-6">
            <div className="relative">
                {isRecording && (
                    <motion.div
                        initial={{ scale: 1, opacity: 0.5 }}
                        animate={{ scale: 2, opacity: 0 }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                        className="absolute inset-0 bg-red-500 rounded-full"
                    />
                )}

                <Button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isProcessing}
                    className={cn(
                        "w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 shadow-xl z-10 relative",
                        isRecording ? "bg-red-500 hover:bg-red-600 shadow-red-500/30" : "bg-brand-blue hover:bg-blue-600 shadow-blue-500/30",
                        isProcessing && "opacity-80 cursor-not-allowed"
                    )}
                >
                    {isProcessing ? (
                        <Loader2 size={40} className="text-white animate-spin" />
                    ) : isRecording ? (
                        <Square size={32} className="text-white fill-current" />
                    ) : (
                        <Mic size={40} className="text-white" />
                    )}
                </Button>
            </div>

            <div className="text-center space-y-1 h-12">
                {isRecording ? (
                    <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex flex-col items-center"
                    >
                        <span className="text-2xl font-mono font-bold text-slate-800 dark:text-slate-200 tracking-wider">
                            {formatTime(duration)}
                        </span>
                        <span className="text-xs text-red-500 font-bold uppercase tracking-widest animate-pulse">Recording</span>
                    </motion.div>
                ) : isProcessing ? (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-1"
                    >
                        <p className="text-sm font-medium text-brand-blue">{processingStep || "Processing..."}</p>
                        {uploadProgress !== undefined && uploadProgress > 0 && uploadProgress < 100 && (
                            <div className="w-48 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mx-auto mt-2">
                                <motion.div
                                    className="h-full bg-brand-blue rounded-full"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${uploadProgress}%` }}
                                />
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <p className="text-sm text-slate-400 dark:text-slate-500 font-medium">Tap to speak</p>
                )}
            </div>
        </div>
    );
});

export default AudioRecorder;

