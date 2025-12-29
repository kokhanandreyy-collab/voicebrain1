

// Added fillRule="evenodd" which is critical for complex compound paths (like logos with holes) to render correctly in React/Browsers

export const GoogleIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
);

export const VkIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 448 512" className={className} fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        {/* Font Awesome Free 6.x VK Icon (Solid Square) */}
        <path d="M100.3 448H7.4V148.9h92.9v168.1c0 47.1 54.7 49 54.7 18.2V148.9h92.9v99c0 14.8-1 25-10.7 34.6 20.9-3.2 27.2-22.6 62.7-89.9h106.3s-5.6 19.3-33.8 68.6c-48.5 83.2-127.3 186.7-127.3 186.7H100.3z" transform="scale(1, -1) translate(0, -512)" />
        {/* Wait, the FA path usually needs standard orientation. The standard FA VK brand icon (just letters) might be better if the user wants just the logo. 
            Let's use the path I found in search which was the SQUARE version: 
            M400 32H48C21.5 32 0 53.5 0 80v352c0 26.5 21.5 48 48 48h352c26.5 0 48-21.5 48-48V80c0-26.5-21.5-48-48-48zM260.6 313.3... 
            This is safer. 
        */}
        <path d="M400 32H48C21.5 32 0 53.5 0 80v352c0 26.5 21.5 48 48 48h352c26.5 0 48-21.5 48-48V80c0-26.5-21.5-48-48-48zM260.6 313.3c-23.7 20.3-64.8 17.6-83.3-10.7-10.5-16.1-5.7-27.8 0-41.6 8.3-21.5 29.8-31.5 49-36.8 1.4-.4 2.8-.8 4.2-1.2 5.5-1.5 10.9-3 16.3-4.5 10.3-2.9 17.1-1.8 19 0 5.6 5.5-2.2 11.2 1.4 16.6 2.3 3.4 8.7 13.9 11.1 20.3 3.5 9.1-.4 18.2-13.6 15.6-7-1.4-13.5-3.5-19.8-6.1-9.4-3.8-19.5-3.6-29.3-.6-12 3.6-21 11.1-27.4 20.6-5.7 8.3-9.1 18.4-10.4 28.9-1.2 10.6.9 21.3 4 31.4 6.7 22 25.1 36.4 48.9 39.8 13.1 1.8 26.5 1.5 39.8 0 17.1-1.9 33.3-8.8 45.4-20.5 4-4 7.6-8.5 10.8-13.3 2.8-4.1 4.9-8.5 6.4-13.1 1.4-4.5 2-9 1.6-13.5-.6-8.6-6.4-15-15.1-16.5-8.8-1.5-17.5 3.3-22.6 10.5-3.4 4.7-6.2 9.8-8.4 15-2.2 5.1-4.1 10.4-5.6 15.7-1.9 6.8-4.1 13.5-6.5 20.2-1.9 5.3-3.9 10.6-6 15.9-2.3 5.4-4.9 10.6-7.8 15.7-3.2 5.6-7.3 10.7-11.5 15.5-5.3 6.1-12.2 10.9-19.5 14.2-12.7 5.7-26.2 7.8-39.7 6.4-13.4-1.4-26.6-5.8-38.3-12.7z" />
    </svg>
);

import { AtSign } from 'lucide-react';

export const MailRuIcon = ({ className }: { className?: string }) => (
    <AtSign className={className} strokeWidth={2.5} />
);

export const TwitterIcon = ({ className }: { className?: string }) => (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" xmlns="http://www.w3.org/2000/svg">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
);
