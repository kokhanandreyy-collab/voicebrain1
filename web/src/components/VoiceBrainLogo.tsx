

export const VoiceBrainLogo = ({ className = "w-6 h-6", color = "currentColor" }: { className?: string, color?: string }) => {
    return (
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            {/* Brain/Mic Head */}
            <path d="M12 3c-2.8 0-5 2.2-5 5v3c0 2.8 2.2 5 5 5s5-2.2 5-5V8c0-2.8-2.2-5-5-5z" />
            {/* Brain Circuitry inside */}
            <path d="M12 3v3" strokeWidth="1.5" className="opacity-70" />
            <path d="M10 5s-1 1-1 2" strokeWidth="1.5" className="opacity-70" />
            <path d="M14 5s1 1 1 2" strokeWidth="1.5" className="opacity-70" />
            <path d="M12 16v-2" strokeWidth="1.5" className="opacity-70" />
            <path d="M9 13s1 1 2 1" strokeWidth="1.5" className="opacity-70" />
            <path d="M15 13s-1 1-2 1" strokeWidth="1.5" className="opacity-70" />

            {/* Mic Stand/Base */}
            <path d="M19 11v2a7 7 0 0 1-14 0v-2" />
            <path d="M12 20v3" />
            <path d="M8 23h8" />
        </svg>
    );
};
