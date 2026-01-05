# VoiceBrain Architecture

This document describes the high-level architecture and design decisions for VoiceBrain.

## System Components

### 1. API Service (FastAPI)
The entry point for all client applications (Web, Desktop, Telegram).
- **Stateless**: Scales horizontally.
- **Middleware**: Handles Authentication (JWT), Rate Limiting (Redis), and CORS.
- **Routers**: Organized by domain (`notes`, `users`, `integrations`).
- **Dependency Injection**: Database sessions, User context, and Services are injected via FastAPI dependencies.

### 2. Async Workers (Celery + Redis)
Handling CPU-bound and I/O-heavy operations off the main thread.
- **Transcribe Task**: Uploads audio to S3, calls speech-to-text APIs.
- **Analyze Task**: Runs the RAG pipeline, calls LLMs (OpenAI/DeepSeek), updates Identity.
- **Sync Task**: Pushes processed notes to external providers (Notion, Google, etc.).
- **Maintenance Task**: Daily memory consolidation and cleanup.

### 3. Data Layer
- **PostgreSQL (with pgvector)**:
    - `users`: Profiles, tiers, preferences.
    - `notes`: Metadata, content, sync status.
    - `note_embeddings`: Vector embeddings for semantic search (1536d).
    - `integrations`: OAuth tokens (encrypted) and configs.
- **Redis**:
    - **Celery Broker/Backend**: Task queue management.
    - **Short-Term Memory**: Storing recent user actions for context.
    - **Rate Limiting**: Tracking request counters.
- **Object Storage (S3)**: Storing raw audio files.

## Intelligence Pipeline (The "Brain")

The core logic resides in `app/services/pipeline.py` and `app/core/analyze_core.py`.

### Principles
1.  **Context-First**: Every analysis is preceded by a RAG lookup (Medium-term) and an Identity injection (Long-term).
2.  **Adaptive**: The system updates the user's `adaptive_preferences` and `identity_summary` based on the content of notes and manual feedback.
3.  **Resilient**: Stages (Transcribe, Analyze, Sync) are isolated with retries. Failures in one stage don't catastrophically break the data.

### ENA-Inspired Memory
*   **Active Context (Short-Term)**: "What just happened?" (Redis List)
*   **Associative Memory (Medium-Term)**: "What is related?" (Vector Search + Note Graph)
*   **Crystalized Memory (Long-Term)**: "What do I know about the user?" (Identity Column + Summarized LongTermMemory table)

## Security
*   **Token Encryption**: OAuth tokens are encrypted at rest using `Fernet` (symmetric encryption).
*   **Rate Limiting**: Tier-based limits applied per IP and per User.
*   **Input Validation**: Strict Pydantic models and file type checking.

## Parity Guidelines
All clients (Web, Desktop, Telegram) typically consume the same API.
- **Telegram**: Uses `run_bot.py` via `aiogram` but calls internal service layers or API endpoints.
- **Web/Desktop**: Consume REST API directly.
