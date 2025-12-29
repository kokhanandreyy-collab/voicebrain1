import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
    onStartRecording: (callback: () => void) => {
        ipcRenderer.on('start-recording', (_event, value) => callback());
    }
});
