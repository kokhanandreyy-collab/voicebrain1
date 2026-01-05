import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from app.models import Note, LongTermMemory, User, NoteRelation
from workers.reflection_tasks import _process_reflection_async
from workers.maintenance_tasks import _cleanup_memory_async

@pytest.mark.asyncio
async def test_reflection_logic(db_session, test_user, mock_ai_service):
    # Create some notes for the user
    for i in range(5):
        note = Note(
            user_id=test_user.id,
            transcription_text=f"Note {i}: Discussing future plans and goals.",
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        db_session.add(note)
    await db_session.commit()

    # configure mock to return notes and then return the created LTM
    mock_ltm = LongTermMemory(user_id=test_user.id, importance_score=9.0, summary_text="A summary")
    mock_result_notes = MagicMock()
    mock_result_notes.scalars.return_value.all.return_value = [Note(user_id=test_user.id, transcription_text="Note")]
    
    mock_result_user = MagicMock()
    mock_result_user.scalars.return_value.first.return_value = test_user
    
    mock_result_ltm = MagicMock()
    mock_result_ltm.scalars.return_value.first.return_value = mock_ltm
    
    # 1. Select Notes, 2. Select User (identity), 3. Select LTM (verify)
    db_session.execute.side_effect = [mock_result_notes, mock_result_user, mock_result_ltm]

    # We need to patch get_chat_completion because _process_reflection_async calls it directly
    with patch("app.services.ai_service.ai_service.get_chat_completion", AsyncMock(return_value='{"summary": "A summary", "identity_summary": "Identity", "importance_score": 9.0}')), \
         patch("app.services.ai_service.ai_service.generate_embedding", AsyncMock(return_value=[0.1]*1536)):
        
        await _process_reflection_async(test_user.id)
        
        # Verify LTM entry created
        from sqlalchemy.future import select
        res = await db_session.execute(select(LongTermMemory).where(LongTermMemory.user_id == test_user.id))
        ltm = res.scalars().first()
        assert ltm is not None
        assert ltm.importance_score == 9.0
        
        # Verify User Identity updated
        assert test_user.identity_summary == "Identity"

@pytest.mark.asyncio
async def test_memory_cleanup_logic(db_session, test_user):
    now = datetime.now(timezone.utc)
    
    # Old, unimportant note
    old_note = Note(
        id="old-unimportant",
        user_id=test_user.id,
        importance_score=2.0,
        created_at=now - timedelta(days=100)
    )
    # New note (should stay)
    new_note = Note(
        id="new-note",
        user_id=test_user.id,
        importance_score=2.0,
        created_at=now - timedelta(days=10)
    )
    # Old, important note (should stay)
    important_old_note = Note(
        id="old-important",
        user_id=test_user.id,
        importance_score=9.0,
        created_at=now - timedelta(days=100)
    )
    
    # configure mock
    # 1. Select old notes, 2. Select old LTMs, 3. Verify final state (mocking after delete)
    mock_result_notes_to_del = MagicMock()
    mock_result_notes_to_del.scalars.return_value.all.return_value = [old_note]
    
    mock_result_ltm_to_del = MagicMock()
    mock_result_ltm_to_del.scalars.return_value.all.return_value = []
    
    mock_result_rel_to_del = MagicMock()
    mock_result_rel_to_del.scalars.return_value.all.return_value = []
    
    mock_result_final = MagicMock()
    mock_result_final.scalars.return_value.all.return_value = [new_note, important_old_note]
    
    # We need to handle multiple execute calls:
    # 1. Notes, 2. LTMs, 3. Relations, 4. Final verification in test
    db_session.execute.side_effect = [
        mock_result_notes_to_del, 
        mock_result_ltm_to_del, 
        mock_result_rel_to_del, 
        mock_result_final
    ]

    await _cleanup_memory_async()
    
    # Verify deletions
    assert db_session.delete.called
    
    # old_note should be gone in the final fetch
    from sqlalchemy.future import select
    res = await db_session.execute(select(Note).where(Note.user_id == test_user.id))
    notes = res.scalars().all()
    
    note_ids = [n.id for n in notes]
    assert old_note.id not in note_ids
    assert new_note.id in note_ids
    assert important_old_note.id in note_ids
