export { };

declare global {
    interface Window {
        electronAPI?: {
            onStartRecording: (callback: () => void) => void;
        };
    }
}
