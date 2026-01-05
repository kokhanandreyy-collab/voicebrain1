import pytest
from unittest.mock import patch
from workers.transcribe_tasks import process_transcribe
from workers.analyze_tasks import process_analyze
from workers.maintenance_tasks import cleanup_memory_task

@patch("app.services.pipeline.pipeline.process")
def test_transcribe_task_wrapper(mock_pipeline):
    process_transcribe("note_123")
    mock_pipeline.assert_called_once_with("note_123")

@patch("app.services.pipeline.pipeline.process")
def test_analyze_task_wrapper(mock_pipeline):
    process_analyze("note_456")
    mock_pipeline.assert_called_once_with("note_456")

@patch("workers.maintenance_tasks._cleanup_memory_async")
def test_cleanup_memory_task_wrapper(mock_cleanup):
    cleanup_memory_task()
    # Since it uses async_to_sync, it calls the internal async function
    assert mock_cleanup.called
