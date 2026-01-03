# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for inference_engine.py
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from src.inference_engine import WhisperNPU


class TestWhisperNPU:
    """Test suite for WhisperNPU inference engine."""
    
    def test_initialization_defaults(self):
        """Test WhisperNPU initialization with defaults."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU()
            
            assert engine.model_path is not None
            assert engine.use_npu is True
            assert engine.encoder_session is None
            assert engine.decoder_session is None
    
    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(
                model_path="/custom/model.onnx",
                use_npu=False
            )
            
            assert engine.model_path == "/custom/model.onnx"
            assert engine.use_npu is False
    
    def test_initialization_missing_model(self):
        """Test initialization with missing model file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                WhisperNPU(model_path="/nonexistent/model.onnx")
    
    def test_load_model_cpu(self, mock_onnxruntime):
        """Test loading model with CPU execution provider."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=False)
            
            with patch('onnxruntime.InferenceSession') as mock_session:
                engine.load_model()
                
                assert mock_session.called
                assert engine.encoder_session is not None
    
    def test_load_model_npu(self, mock_onnxruntime):
        """Test loading model with VitisAI execution provider."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=True)
            
            with patch('onnxruntime.InferenceSession') as mock_session:
                with patch('onnxruntime.get_available_providers', 
                          return_value=['VitisAIExecutionProvider', 'CPUExecutionProvider']):
                    engine.load_model()
                    
                    assert mock_session.called
    
    def test_load_model_missing_vitis_provider(self, mock_onnxruntime):
        """Test loading model when VitisAI provider is unavailable."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=True)
            
            with patch('onnxruntime.get_available_providers',
                      return_value=['CPUExecutionProvider']):
                # Should fall back to CPU
                engine.load_model()
                
                # Should still work, just on CPU
                assert engine.encoder_session is not None
    
    @pytest.mark.asyncio
    async def test_transcribe_basic(self, mock_onnxruntime):
        """Test basic transcription."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=False)
            
            # Mock the model
            mock_encoder = MagicMock()
            mock_decoder = MagicMock()
            
            # Mock encoder output
            mock_encoder.run.return_value = [
                np.random.randn(1, 1500, 512).astype(np.float32)
            ]
            
            # Mock decoder output (token IDs)
            mock_decoder.run.return_value = [
                np.array([[50258, 50259, 50359, 50363, 1234, 5678, 50257]])
            ]
            
            engine.encoder_session = mock_encoder
            engine.decoder_session = mock_decoder
            
            # Mock tokenizer decode
            with patch.object(engine, '_decode_tokens', return_value="test output"):
                audio = np.random.randn(16000).astype(np.float32)
                result = await engine.transcribe(audio)
                
                assert isinstance(result, str)
                assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self, mock_onnxruntime):
        """Test transcription with empty audio."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=False)
            engine.encoder_session = MagicMock()
            engine.decoder_session = MagicMock()
            
            empty_audio = np.array([], dtype=np.float32)
            
            with pytest.raises(ValueError):
                await engine.transcribe(empty_audio)
    
    @pytest.mark.asyncio
    async def test_transcribe_without_model(self):
        """Test transcription without loading model first."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU()
            
            audio = np.random.randn(16000).astype(np.float32)
            
            with pytest.raises(RuntimeError, match="Model not loaded"):
                await engine.transcribe(audio)
    
    def test_preprocess_audio(self):
        """Test audio preprocessing for model input."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU()
            
            # 1 second of audio at 16kHz
            audio = np.random.randn(16000).astype(np.float32)
            
            processed = engine._preprocess_audio(audio)
            
            assert isinstance(processed, np.ndarray)
            assert processed.dtype == np.float32
            # Whisper expects 30-second chunks (480000 samples)
            assert len(processed) == 480000
    
    def test_mel_spectrogram_generation(self):
        """Test mel spectrogram generation."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU()
            
            # 30 seconds of audio
            audio = np.random.randn(480000).astype(np.float32)
            
            mel = engine._compute_mel_spectrogram(audio)
            
            assert isinstance(mel, np.ndarray)
            # Whisper uses 80 mel bins and 3000 time steps for 30s
            assert mel.shape == (80, 3000)
    
    def test_decode_tokens(self):
        """Test token decoding to text."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU()
            
            # Mock token IDs (special tokens + some text)
            tokens = np.array([50258, 50259, 50359, 50363, 1234, 5678, 50257])
            
            with patch('tiktoken.get_encoding') as mock_encoding:
                mock_enc = MagicMock()
                mock_enc.decode.return_value = "test transcription"
                mock_encoding.return_value = mock_enc
                
                result = engine._decode_tokens(tokens)
                
                assert isinstance(result, str)
                assert len(result) > 0
    
    def test_warmup_inference(self, mock_onnxruntime):
        """Test warmup inference with dummy audio."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=False)
            
            mock_encoder = MagicMock()
            mock_decoder = MagicMock()
            mock_encoder.run.return_value = [np.random.randn(1, 1500, 512)]
            mock_decoder.run.return_value = [np.array([[50257]])]
            
            engine.encoder_session = mock_encoder
            engine.decoder_session = mock_decoder
            
            # Should complete without errors
            engine.warmup()
            
            assert mock_encoder.run.called
            assert mock_decoder.run.called
    
    @pytest.mark.asyncio
    async def test_concurrent_transcription(self, mock_onnxruntime):
        """Test multiple concurrent transcription requests."""
        with patch('os.path.exists', return_value=True):
            engine = WhisperNPU(use_npu=False)
            
            mock_encoder = MagicMock()
            mock_decoder = MagicMock()
            mock_encoder.run.return_value = [np.random.randn(1, 1500, 512)]
            mock_decoder.run.return_value = [np.array([[50257]])]
            
            engine.encoder_session = mock_encoder
            engine.decoder_session = mock_decoder
            
            with patch.object(engine, '_decode_tokens', return_value="test"):
                audio = np.random.randn(16000).astype(np.float32)
                
                # Run multiple transcriptions concurrently
                results = await asyncio.gather(
                    engine.transcribe(audio),
                    engine.transcribe(audio),
                    engine.transcribe(audio)
                )
                
                assert len(results) == 3
                assert all(isinstance(r, str) for r in results)
