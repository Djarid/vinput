# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for main.py orchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.main import VoiceInputOrchestrator


class TestVoiceInputOrchestrator:
    """Test suite for VoiceInputOrchestrator class."""
    
    def test_initialization(self, sample_commands):
        """Test orchestrator initialization."""
        with patch('builtins.open', create=True) as mock_open:
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                assert orchestrator.commands is not None
                assert 'commands' in orchestrator.commands
    
    def test_load_commands(self, sample_commands):
        """Test command loading from YAML."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                orchestrator._load_commands()
                
                assert 'jump' in orchestrator.commands['commands']
                assert 'crouch' in orchestrator.commands['commands']
    
    def test_load_commands_missing_file(self):
        """Test command loading with missing file."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                orchestrator = VoiceInputOrchestrator()
    
    def test_match_command_exact(self, sample_commands):
        """Test exact command matching."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                command = orchestrator._match_command("jump")
                
                assert command is not None
                assert command['type'] == 'button'
                assert command['button'] == 'A'
    
    def test_match_command_case_insensitive(self, sample_commands):
        """Test case-insensitive command matching."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                command = orchestrator._match_command("JUMP")
                assert command is not None
                
                command = orchestrator._match_command("JuMp")
                assert command is not None
    
    def test_match_command_partial(self, sample_commands):
        """Test partial command matching."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                # "move forward" should match even if we say "move"
                command = orchestrator._match_command("move forward now")
                assert command is not None
    
    def test_match_command_no_match(self, sample_commands):
        """Test command matching with no match."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                command = orchestrator._match_command("invalid command")
                assert command is None
    
    @pytest.mark.asyncio
    async def test_execute_button_action(self, sample_commands, mock_uinput):
        """Test executing button action."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                # Mock controller
                orchestrator.controller = MagicMock()
                orchestrator.controller.tap_button = AsyncMock()
                
                action = {'type': 'button', 'button': 'A', 'duration': 50}
                await orchestrator._execute_action(action)
                
                orchestrator.controller.tap_button.assert_called_once_with('A', duration_ms=50)
    
    @pytest.mark.asyncio
    async def test_execute_stick_action(self, sample_commands, mock_uinput):
        """Test executing stick action."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                orchestrator.controller.move_stick = AsyncMock()
                
                action = {
                    'type': 'stick',
                    'stick': 'left',
                    'x': 0,
                    'y': -32768,
                    'duration': 1000
                }
                await orchestrator._execute_action(action)
                
                orchestrator.controller.move_stick.assert_called_once_with(
                    'left', 0, -32768, duration_ms=1000
                )
    
    @pytest.mark.asyncio
    async def test_execute_sequence_action(self, sample_commands, mock_uinput):
        """Test executing sequence of actions."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                orchestrator.controller.tap_button = AsyncMock()
                
                action = sample_commands['commands']['combo']
                await orchestrator._execute_action(action)
                
                # Should have called tap_button twice (X and Y)
                assert orchestrator.controller.tap_button.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_trigger_action(self, sample_commands, mock_uinput):
        """Test executing trigger action."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                orchestrator.controller.move_trigger = AsyncMock()
                
                action = {'type': 'trigger', 'trigger': 'left', 'value': 255}
                await orchestrator._execute_action(action)
                
                orchestrator.controller.move_trigger.assert_called_once_with('left', value=255)
    
    @pytest.mark.asyncio
    async def test_execute_dpad_action(self, sample_commands, mock_uinput):
        """Test executing D-pad action."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                orchestrator.controller.move_dpad = AsyncMock()
                
                action = {'type': 'dpad', 'direction': 'up'}
                await orchestrator._execute_action(action)
                
                orchestrator.controller.move_dpad.assert_called_once_with('up')
    
    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, sample_commands):
        """Test executing unknown action type."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                
                action = {'type': 'unknown_type'}
                
                # Should not raise exception, just log warning
                await orchestrator._execute_action(action)
    
    @pytest.mark.asyncio
    async def test_process_transcription(self, sample_commands, mock_uinput):
        """Test processing transcribed text."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                orchestrator.controller.tap_button = AsyncMock()
                
                # Process a command
                await orchestrator._process_transcription("jump")
                
                orchestrator.controller.tap_button.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_transcription_no_match(self, sample_commands):
        """Test processing text with no matching command."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                orchestrator.controller = MagicMock()
                
                # Should not raise exception
                await orchestrator._process_transcription("unknown command")
    
    @pytest.mark.asyncio
    async def test_run_orchestrator(self, sample_commands, mock_sounddevice, mock_onnxruntime, mock_uinput):
        """Test running the full orchestrator."""
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=sample_commands):
                orchestrator = VoiceInputOrchestrator()
                
                # Mock components
                orchestrator.audio_engine = MagicMock()
                orchestrator.audio_engine.start = AsyncMock()
                orchestrator.audio_engine.detect_speech = AsyncMock(
                    side_effect=asyncio.CancelledError
                )
                orchestrator.audio_engine.stop = AsyncMock()
                
                orchestrator.inference_engine = MagicMock()
                orchestrator.controller = MagicMock()
                orchestrator.controller.initialize = Mock()
                orchestrator.controller.shutdown = Mock()
                
                # Should handle cancellation gracefully
                with pytest.raises(asyncio.CancelledError):
                    await orchestrator.run()
                
                # Cleanup should be called
                orchestrator.controller.shutdown.assert_called_once()
