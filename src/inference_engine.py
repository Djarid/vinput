# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Inference engine for vinput.
Wraps ONNX Runtime with Vitis AI Execution Provider for NPU acceleration.
"""

import os
import numpy as np
import onnxruntime as ort
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class WhisperNPU:
    """Wrapper for Whisper model running on XDNA 2 NPU via ONNX Runtime."""

    def __init__(
        self,
        encoder_model_path: str,
        decoder_model_path: str,
        vaip_config_path: str,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Whisper NPU inference engine.

        Args:
            encoder_model_path: Path to quantized Whisper encoder ONNX model
            decoder_model_path: Path to quantized Whisper decoder ONNX model
            vaip_config_path: Path to vaip_config.json for Vitis AI compiler
            cache_dir: Directory for caching compiled models (optional)
        """
        self.encoder_model_path = encoder_model_path
        self.decoder_model_path = decoder_model_path
        self.vaip_config_path = vaip_config_path
        self.cache_dir = cache_dir or "/tmp/vinput_cache"
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.encoder_session = None
        self.decoder_session = None
        self._is_initialized = False
        
        logger.info("WhisperNPU engine instantiated (models not yet loaded)")

    def initialize(self) -> None:
        """
        Initialize ONNX Runtime sessions.
        Loads encoder and decoder models with Vitis AI Execution Provider.
        """
        if self._is_initialized:
            logger.warning("WhisperNPU already initialized")
            return
        
        try:
            # Vitis AI provider options
            vitis_ai_options = {
                'config_file_path': self.vaip_config_path,
                'cache_dir': self.cache_dir,
                'cache_key': 'whisper_quantized',
            }
            
            provider_list = [
                ('VitisAIExecutionProvider', vitis_ai_options),
                'CPUExecutionProvider'
            ]
            
            logger.info("Loading encoder model...")
            self.encoder_session = ort.InferenceSession(
                self.encoder_model_path,
                providers=provider_list
            )
            logger.info(
                f"Encoder loaded. Providers: {self.encoder_session.get_providers()}"
            )
            
            logger.info("Loading decoder model...")
            self.decoder_session = ort.InferenceSession(
                self.decoder_model_path,
                providers=provider_list
            )
            logger.info(
                f"Decoder loaded. Providers: {self.decoder_session.get_providers()}"
            )
            
            self._is_initialized = True
            logger.info("WhisperNPU fully initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ONNX sessions: {e}")
            raise

    async def warm_up(self) -> None:
        """
        Warm up the NPU by running dummy inference.
        Ensures the firmware graph is loaded before actual use.
        """
        if not self._is_initialized:
            logger.warning("WhisperNPU not initialized; skipping warm-up")
            return
        
        try:
            logger.info("Warming up NPU with dummy inference...")
            # Create dummy input (480,000 samples of silence)
            dummy_audio = np.zeros(480_000, dtype=np.float32)
            
            # Run through encoder
            encoder_input_name = self.encoder_session.get_inputs()[0].name
            encoder_inputs = {encoder_input_name: dummy_audio[np.newaxis, :].astype(np.float32)}
            encoder_output = self.encoder_session.run(None, encoder_inputs)
            
            logger.info("NPU warm-up complete")
        except Exception as e:
            logger.warning(f"Warm-up failed (non-critical): {e}")

    def _ensure_contiguous(self, array: np.ndarray) -> np.ndarray:
        """Ensure array is contiguous in memory for IOMMU compatibility."""
        if not array.flags['C_CONTIGUOUS']:
            return np.ascontiguousarray(array)
        return array

    def encode(self, audio: np.ndarray) -> np.ndarray:
        """
        Encode audio using the encoder model.

        Args:
            audio: Preprocessed audio (float32, 480,000 samples)

        Returns:
            Encoder output (typically embeddings or encoded features)
        """
        if not self._is_initialized:
            raise RuntimeError("WhisperNPU not initialized. Call initialize() first.")
        
        # Ensure contiguity for DMA
        audio_contiguous = self._ensure_contiguous(audio)
        
        # Add batch dimension if needed
        if audio_contiguous.ndim == 1:
            audio_contiguous = audio_contiguous[np.newaxis, :]
        
        # Ensure float32
        audio_contiguous = audio_contiguous.astype(np.float32)
        
        try:
            encoder_input_name = self.encoder_session.get_inputs()[0].name
            encoder_inputs = {encoder_input_name: audio_contiguous}
            
            logger.debug(f"Encoder input shape: {audio_contiguous.shape}")
            
            encoder_output = self.encoder_session.run(None, encoder_inputs)
            
            logger.debug(f"Encoder output shapes: {[o.shape for o in encoder_output]}")
            
            return encoder_output
        except Exception as e:
            logger.error(f"Encoder inference failed: {e}")
            raise

    def decode(self, encoder_output: list, max_tokens: int = 128) -> str:
        """
        Decode encoder output to text using greedy decoding.

        Args:
            encoder_output: Output from encoder (list of arrays)
            max_tokens: Maximum tokens to generate

        Returns:
            Decoded text transcription
        """
        if not self._is_initialized:
            raise RuntimeError("WhisperNPU not initialized. Call initialize() first.")
        
        try:
            # Initialize with empty token sequence
            token_ids = []
            
            # Prepare encoder context (first output from encoder)
            encoder_context = encoder_output[0]
            encoder_context = self._ensure_contiguous(encoder_context)
            
            # Greedy decoding loop
            for step in range(max_tokens):
                # Prepare decoder inputs
                # This is a simplified version; actual implementation depends on model architecture
                decoder_input_ids = np.array([token_ids + [1]], dtype=np.int64)  # 1 = BOS token
                
                decoder_inputs = {
                    self.decoder_session.get_inputs()[0].name: decoder_input_ids,
                    self.decoder_session.get_inputs()[1].name: encoder_context,
                }
                
                decoder_output = self.decoder_session.run(None, decoder_inputs)
                
                # Get next token (greedy: argmax)
                logits = decoder_output[0]
                next_token = np.argmax(logits[0, -1, :])
                
                # End-of-sequence token
                if next_token == 2:  # 2 = EOS token
                    break
                
                token_ids.append(int(next_token))
            
            logger.debug(f"Decoded {len(token_ids)} tokens")
            
            # Convert token IDs to text (simplified; actual tokenizer depends on model)
            # In a real implementation, use the model's tokenizer
            text = f"<placeholder_transcription_from_{len(token_ids)}_tokens>"
            
            return text
        except Exception as e:
            logger.error(f"Decoder inference failed: {e}")
            raise

    async def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio to text.
        Runs encoder and decoder in sequence.

        Args:
            audio: Preprocessed audio (float32, 480,000 samples)

        Returns:
            Transcribed text
        """
        if not self._is_initialized:
            raise RuntimeError("WhisperNPU not initialized. Call initialize() first.")
        
        try:
            logger.info("Starting transcription...")
            
            # Encode audio
            encoder_output = self.encode(audio)
            
            # Decode to text
            text = self.decode(encoder_output)
            
            logger.info(f"Transcription complete: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def shutdown(self) -> None:
        """Clean up resources."""
        if self.encoder_session:
            del self.encoder_session
            self.encoder_session = None
        if self.decoder_session:
            del self.decoder_session
            self.decoder_session = None
        self._is_initialized = False
        logger.info("WhisperNPU shut down")
