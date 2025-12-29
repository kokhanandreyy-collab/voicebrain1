import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Log Capture for Feedback
// @ts-ignore
window.consoleLogs = [];
const MAX_LOGS = 50;
const captureLog = (type: string, args: any[]) => {
    // @ts-ignore
    if (!window.consoleLogs) window.consoleLogs = [];
    // @ts-ignore
    window.consoleLogs.push({ type, time: new Date().toISOString(), data: args.map(a => String(a)) });
    // @ts-ignore
    if (window.consoleLogs.length > MAX_LOGS) window.consoleLogs.shift();
};

const originalLog = console.log;
const originalWarn = console.warn;
const originalError = console.error;

console.log = (...args) => { captureLog('log', args); originalLog(...args); };
console.warn = (...args) => { captureLog('warn', args); originalWarn(...args); };
console.error = (...args) => { captureLog('error', args); originalError(...args); };

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(
            (registration) => {
                console.log('ServiceWorker registration successful with scope: ', registration.scope);
            },
            (err) => {
                console.log('ServiceWorker registration failed: ', err);
            }
        );
    });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
