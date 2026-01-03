import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat, User
from telegram.handlers.chat import cmd_start, cmd_help

@pytest.mark.asyncio
async def test_cmd_start():
    message = AsyncMock(spec=Message)
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 123
    command = MagicMock()
    command.args = None
    
    await cmd_start(message, command)
    
    # Check if answer was called
    assert message.answer.called
    args, kwargs = message.answer.call_args
    assert "Welcome" in args[0]

@pytest.mark.asyncio
async def test_cmd_help():
    message = AsyncMock(spec=Message)
    await cmd_help(message)
    assert message.answer.called
    args, kwargs = message.answer.call_args
    assert "Help" in args[0]

@pytest.mark.asyncio
async def test_cmd_new_note():
    from telegram.handlers.notes import cmd_new_note
    message = AsyncMock(spec=Message)
    message.chat.id = 123
    state = AsyncMock()
    
    # Mocking get_api_key
    with patch("telegram.handlers.notes.get_api_key", return_value="fake_key"):
        await cmd_new_note(message, state)
        assert message.answer.called
        assert "Please send the text" in message.answer.call_args[0][0]
        assert state.set_state.called
