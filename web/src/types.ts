export interface IntegrationStatus {
    provider: string;
    status: 'SUCCESS' | 'FAILED' | 'PENDING';
    timestamp: string;
    error?: string;
}

export interface Note {
    id: string;
    title?: string;
    transcription_text?: string;
    summary?: string;
    action_items?: string[];
    tags?: string[];
    mood?: string;
    audio_url?: string;
    created_at: string;
    status?: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    processing_error?: string;
    processing_step?: string;
    health_data?: {
        nutrition?: {
            calories: number;
            protein: number;
            carbs: number;
            fat: number;
            water_ml: number;
            name: string;
        };
        workout?: {
            type: string;
            duration_minutes: number;
            calories_burned: number;
        };
        symptoms?: string[];
        trend_compliment?: string;
    };
    ai_analysis?: any;
    integration_status?: IntegrationStatus[];
}

export interface User {
    id: string;
    email: string;
    full_name?: string;
    tier?: string;
}

export interface Integration {
    id: string;
    user_id: string;
    provider: string;
    settings?: {
        workspace_name?: string;
        webhook_url?: string;
        auto_trigger_new_note?: boolean;
        [key: string]: any;
    };
    created_at: string;
    is_active?: boolean;
    status?: 'active' | 'auth_error' | 'rate_limited';
    error_message?: string;
}

export interface RelatedNote {
    id: string;
    title: string;
    summary?: string;
    created_at: string;
    similarity: number;
}
