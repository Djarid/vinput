# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for audio_engine.py
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.audio_engine import AudioEngine


class TestAudioEngine:
    """Test suite for AudioEngine class."""
    
    def test_initialization(self):
        """Test AudioEngine initialization with default parameters."""
        engine = AudioEngine()
        
        assert engine.sample_rate == 16000
        assert engine.channels == 1
        assert engine.vad_aggressiveness == 3
        assert engine.frame_duration_ms == 30
        assert engine.is_running is False
    
    def test_initialization_custom_params(self):
        """Test AudioEngine initialization with custom parameters."""
        engine = AudioEngine(
            sample_rate=8000,
            channels=2,
            vad_aggressiveness=2
        )
        
        assert engine.sample_rate == 8000
        assert engine.channels == 2
        assert engine.vad_aggressiveness == 2
    
    @pytest.mark.asyncio
    async def test_start_stop(self, mock_sounddevice):
        """Test starting and stopping audio engine."""
        engine = AudioEngine()
        
        await engine.start()
        assert engine.is_running is True
        
        await engine.stop()
        assert engine.is_running is False
    
    @pytest.mark.asyncio
    async def test_audio_callback_with_speech(self, mock_sounddevice):
        """Test audio callback when speech is detected."""
        engine = AudioEngine()
        
        # Mock VAD to detect speech
        with patch.object(engine.vad, 'is_speech', return_value=True):
            # Simulate audio data
            indata = np.random.randn(480, 1).astype(np.float32)
            
            await engine.start()
            engine._audio_callback(indata, 480, None, None)
            
            # Check that audio was added to buffer
            assert engine.audio_buffer.qsize() > 0
            
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_audio_callback_without_speech(self, mock_sounddevice):
        """Test audio callback when no speech is detected."""
        engine = AudioEngine()
        
        # Mock VAD to not detect speech
        with patch.object(engine.vad, 'is_speech', return_value=False):
            indata = np.random.randn(480, 1).astype(np.float32)
            
            await engine.start()
            initial_size = engine.audio_buffer.qsize()
            engine._audio_callback(indata, 480, None, None)
            
            # Buffer should not grow significantly without speech
            assert engine.audio_buffer.qsize() == initial_size
            
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_detect_speech_timeout(self, mock_sounddevice):
        """Test speech detection with timeout."""
        engine = AudioEngine()
        
        await engine.start()
        
        # Should timeout if no speech detected
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                engine.detect_speech(buffer_ms=100),
                timeout=0.5
            )
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_detect_speech_returns_audio(self, mock_sounddevice):
        """Test that detect_speech returns audio data when available."""
        engine = AudioEngine()
        
        await engine.start()
        
        # Manually add audio to buffer
        sample_audio = np.random.randn(480).astype(np.float32)
        await engine.audio_buffer.put(sample_audio)
        
        # Should return audio data
        result = await asyncio.wait_for(
            engine.detect_speech(buffer_ms=100),
            timeout=1.0
        )
        
        assert len(result) > 0
        assert isinstance(result, np.ndarray)
        
        await engine.stop()
    
    def test_preprocess_audio(self):
        """Test audio preprocessing."""
        engine = AudioEngine()
        
        # Create sample audio data
        audio = np.random.randn(16000).astype(np.float32)
        
        # Preprocess
        processed = engine._preprocess_audio(audio)
        
        # Check output shape and type
        assert isinstance(processed, np.ndarray)
        assert processed.dtype == np.float32
        assert len(processed) > 0
    
    def test_normalize_audio(self):
        """Test audio normalization."""
        engine = AudioEngine()
        
        # Create audio with known peak
        audio = np.array([0.5, -0.5, 0.25, -0.25], dtype=np.float32)
        
        normalized = engine._normalize_audio(audio)
        
        # Peak should be near 1.0 or -1.0
        assert np.abs(normalized).max() <= 1.0
        assert np.abs(normalized).max() > 0.9  # Should be close to 1.0
    
    @pytest.mark.asyncio
    async def test_double_start_ignored(self, mock_sounddevice):
        """Test that calling start() twice doesn't break."""
        engine = AudioEngine()
        
        await engine.start()
        assert engine.is_running is True
        
        # Second start should be ignored
        await engine.start()
        assert engine.is_running is True
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test that calling stop() without start() is safe."""
        engine = AudioEngine()
        
        # Should not raise exception
        await engine.stop()
        assert engine.is_running is False
