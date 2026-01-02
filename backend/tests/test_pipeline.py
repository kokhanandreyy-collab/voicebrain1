import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.pipeline import NotePipeline
from app.models import Note, User, NoteStatus, Integration
from app.core.analyze_core import AnalyzeCore
from app.core.audio import AudioProcessor
from app.core.sync_service import SyncService

# Mock Dependencies
@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Mock execute/scalars/first/all chain
    result_mock = MagicMock()
    result_mock.scalars().first.return_value = None
    result_mock.scalars().all.return_value = []
    session.execute.return_value = result_mock
    return session

@pytest.fixture
def mock_audio_processor():
    mock = AsyncMock(spec=AudioProcessor)
    return mock

@pytest.fixture
def mock_analyze_core():
    mock = AsyncMock(spec=AnalyzeCore)
    return mock

@pytest.fixture
def mock_sync_service():
    mock = AsyncMock(spec=SyncService)
    return mock

@pytest.fixture
def pipeline(mock_audio_processor, mock_analyze_core, mock_sync_service):
    # Patch dependencies globally or inject if we refactored fully.
    # The pipeline imports instances `audio_processor`, `analyze_core`.
    # We will use `patch` in tests.
    return NotePipeline()

@pytest.mark.asyncio
async def test_pipeline_full_flow(mock_db_session):
    """Test standard flow: Transcribe -> Analyze -> Sync"""
    note_id = "test-note-1"
    
    # Setup Data
    user = User(id="user-1", email="test@test.com", feature_flags={"all_integrations": True})
    note = Note(
        id=note_id, 
        user_id=user.id, 
        status=NoteStatus.PENDING, 
        audio_url="s3://foo.ogg",
        transcription_text=None
    )

    # Mock DB Query Results
    # 1. First fetch (Pending)
    # 2. Refetch for Analyze (Processing)
    # 3. Refetch for Sync (Analyzed)
    # 4. Final status check?
    
    # We can just return the SAME note object reference to simulate state updates on it.
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = note
    
    # Also need to return user when queried inside Analyze step
    def execute_side_effect(query):
        s = str(query)
        if "FROM users" in s:
             m = MagicMock()
             m.scalars().first.return_value = user
             return m
        m = MagicMock()
        m.scalars().first.return_value = note
        return m
        
    mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

    # Mock External Services
    with patch("app.services.pipeline.audio_processor") as mock_audio, \
         patch("app.services.pipeline.analyze_core") as mock_analyze, \
         patch("app.services.pipeline.sync_service") as mock_sync, \
         patch("app.services.pipeline.AsyncSessionLocal") as mock_session_cls:
         
        mock_session_cls.return_value.__aenter__.return_value = mock_db_session
        
        # Simulate processing setting properties
        async def transcribe_side_effect(n, sc):
             n.transcription_text = "Hello world"
             n.status = NoteStatus.PROCESSING
        mock_audio.process_audio.side_effect = transcribe_side_effect

        async def analyze_side_effect(n, u, db, mem):
             n.ai_analysis = {"topics": ["intro"]}
             n.status = NoteStatus.ANALYZED
        mock_analyze.analyze_step.side_effect = analyze_side_effect
        
        pipeline = NotePipeline()
        await pipeline.process(note_id)

        # Verify Calls
        mock_audio.process_audio.assert_called_once()
        mock_analyze.analyze_step.assert_called_once()
        mock_sync.sync_note.assert_called_once()
        
        # Verify final state logic (handled inside sync usually, or pipeline finalizes?)
        # Pipeline usually leaves it at ANALYZED or SYNCED.
        # Check commit calls
        assert mock_db_session.commit.call_count >= 3

@pytest.mark.asyncio
async def test_skip_integrations_by_flag(mock_db_session):
    """Test that sync is skipped if feature flags disable it GLOBAL check."""
    note_id = "test-note-2"
    user = User(id="user-1", feature_flags={"all_integrations": False}) # Global Disable
    note = Note(id=note_id, user_id=user.id, status=NoteStatus.ANALYZED) # Already Analyzed
    
    # Mock DB
    def execute_side_effect(query):
        str_q = str(query)
        if "FROM users" in str_q:
             m = MagicMock()
             m.scalars().first.return_value = user
             return m
        m = MagicMock()
        m.scalars().first.return_value = note
        return m
    mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

    with patch("app.services.pipeline.sync_service") as mock_sync, \
         patch("app.services.pipeline.AsyncSessionLocal") as mock_session_cls:
         
        mock_session_cls.return_value.__aenter__.return_value = mock_db_session
        
        pipeline = NotePipeline()
        await pipeline.process(note_id)
        
        # Pipeline logic (Step 788) checks flag and returns early
        mock_sync.sync_note.assert_not_called()
        assert note.status == NoteStatus.COMPLETED
        assert "Skipped" in note.processing_step

@pytest.mark.asyncio
async def test_integration_explicit_chain(mock_db_session):
    """Test that pipeline passes analyzed note to sync service."""
    note_id = "test-note-chain"
    user = User(id="user-1", feature_flags={"all_integrations": True})
    note = Note(id=note_id, user_id=user.id, status=NoteStatus.ANALYZED)
    note.ai_analysis = {"explicit_destination_app": "linear"} # Chain logic trigger
    
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = note
    
    # Mock user fetch
    def execute_side_effect(query):
        if "FROM users" in str(query):
             m = MagicMock()
             m.scalars().first.return_value = user
             return m
        m = MagicMock()
        m.scalars().first.return_value = note
        return m
    mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

    with patch("app.services.pipeline.sync_service") as mock_sync, \
         patch("app.services.pipeline.AsyncSessionLocal") as mock_session_cls:
         
        mock_session_cls.return_value.__aenter__.return_value = mock_db_session
        
        pipeline = NotePipeline()
        await pipeline.process(note_id)
        
        # Verify sync called (SyncService handles the actual chaining logic)
        mock_sync.sync_note.assert_called_once_with(note, mock_db_session)


@pytest.mark.asyncio
async def test_pipeline_error_handling(mock_db_session):
    """Test error handling setting status to FAILED."""
    note_id = "test-note-3"
    note = Note(id=note_id, status=NoteStatus.PENDING)
    
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = note

    with patch("app.services.pipeline.audio_processor") as mock_audio, \
         patch("app.services.pipeline.AsyncSessionLocal") as mock_session_cls:
         
        mock_session_cls.return_value.__aenter__.return_value = mock_db_session
        
        # Simulate Error
        mock_audio.process_audio.side_effect = Exception("S3 Error")
        
        pipeline = NotePipeline()
        await pipeline.process(note_id)
        
        assert note.status == NoteStatus.FAILED
        assert "S3 Error" in str(note.processing_error)
        mock_db_session.commit.assert_called()

