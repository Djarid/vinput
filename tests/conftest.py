# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module."""
    with patch('sounddevice.InputStream') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_uinput():
    """Mock evdev.UInput for testing input engine without hardware."""
    with patch('evdev.UInput') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_onnxruntime():
    """Mock onnxruntime for testing inference without NPU."""
    with patch('onnxruntime.InferenceSession') as mock:
        mock_session = MagicMock()
        mock_session.run.return_value = [Mock()]
        mock.return_value = mock_session
        yield mock_session


@pytest.fixture
def sample_commands():
    """Sample command configuration for testing."""
    return {
        'commands': {
            'jump': {
                'type': 'button',
                'button': 'A',
                'duration': 50
            },
            'crouch': {
                'type': 'button',
                'button': 'B',
                'duration': 2000
            },
            'move forward': {
                'type': 'stick',
                'stick': 'left',
                'x': 0,
                'y': -32768,
                'duration': 1000
            },
            'combo': {
                'type': 'sequence',
                'actions': [
                    {'type': 'button', 'button': 'X', 'duration': 100},
                    {'type': 'button', 'button': 'Y', 'duration': 100}
                ]
            }
        }
    }
