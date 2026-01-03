"""
Audio acquisition engine for vinput.
Handles async audio capture, voice activity detection, and preprocessing.
"""

import asyncio
import numpy as np
import sounddevice as sd
import webrtcvad
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class AudioEngine:
    """Manages audio capture, VAD, and preprocessing for voice commands."""

    def __init__(
        self,
        sample_rate: int = 16000,
        block_size: int = 1024,
        vad_mode: int = 2,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Initialize the audio engine.

        Args:
            sample_rate: Audio sample rate in Hz (must be 8000, 16000, 32000, or 48000)
            block_size: Sounddevice block size in frames (~60-120ms recommended)
            vad_mode: WebRTC VAD aggressiveness (0=least aggressive, 3=most aggressive)
            loop: asyncio event loop (uses current loop if not provided)
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.vad = webrtcvad.Vad(vad_mode)
        self.loop = loop or asyncio.get_event_loop()
        
        # Audio queue for inter-thread communication
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        
        # State tracking
        self._stream = None
        self._is_running = False
        
        logger.info(
            f"AudioEngine initialized: {sample_rate}Hz, "
            f"block_size={block_size}, vad_mode={vad_mode}"
        )

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """
        Callback for sounddevice stream.
        Called from audio thread; must be thread-safe.
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Convert to int16 for VAD (webrtcvad expects int16)
        audio_data = indata[:, 0] if indata.shape[1] > 1 else indata[:, 0]
        audio_int16 = np.int16(audio_data * 32767)
        
        # Put into queue using thread-safe call_soon_threadsafe
        try:
            self.loop.call_soon_threadsafe(
                self.audio_queue.put_nowait,
                audio_int16.tobytes()
            )
        except asyncio.QueueFull:
            logger.warning("Audio queue full, dropping frames")

    async def start(self) -> None:
        """Start the audio capture stream."""
        if self._is_running:
            logger.warning("Audio stream already running")
            return
        
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.block_size,
                callback=self._audio_callback,
                dtype=np.float32,
            )
            self._stream.start()
            self._is_running = True
            logger.info("Audio stream started")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise

    async def stop(self) -> None:
        """Stop the audio capture stream."""
        if not self._is_running:
            return
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
        self._is_running = False
        logger.info("Audio stream stopped")

    async def detect_speech(self, buffer_ms: int = 500) -> np.ndarray:
        """
        Detect speech activity using VAD and accumulate audio frames.
        
        Args:
            buffer_ms: Silence threshold in milliseconds before returning
        
        Returns:
            NumPy array of accumulated audio samples (int16)
        """
        frames_per_frame = self.block_size
        frame_duration_ms = (frames_per_frame / self.sample_rate) * 1000
        silence_threshold_frames = int(buffer_ms / frame_duration_ms)
        
        accumulated_frames = []
        silence_counter = 0
        in_speech = False
        
        logger.debug("Starting speech detection...")
        
        while True:
            try:
                # Get audio frame from queue with timeout
                audio_bytes = await asyncio.wait_for(
                    self.audio_queue.get(), timeout=2.0
                )
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                
                # Detect voice activity
                is_speech = self.vad.is_speech(audio_bytes, self.sample_rate)
                
                if is_speech:
                    accumulated_frames.append(audio_int16)
                    silence_counter = 0
                    if not in_speech:
                        logger.debug("Speech detected")
                        in_speech = True
                else:
                    # Silence detected
                    if in_speech:
                        silence_counter += 1
                        if silence_counter >= silence_threshold_frames:
                            logger.debug(
                                f"Silence threshold reached "
                                f"({silence_counter} frames)"
                            )
                            break
                        # Keep accumulating a few silence frames for context
                        accumulated_frames.append(audio_int16)
                        
            except asyncio.TimeoutError:
                if in_speech and len(accumulated_frames) > 0:
                    logger.debug("Timeout during speech; returning accumulated audio")
                    break
                logger.debug("Timeout; no speech detected")
                raise

        if accumulated_frames:
            result = np.concatenate(accumulated_frames)
            logger.info(f"Accumulated {len(result)} audio samples")
            return result
        return np.array([], dtype=np.int16)

    async def preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Preprocess audio for inference.
        - Pad or truncate to fixed 480,000 samples (30 seconds at 16kHz)
        - Convert to float32
        - Ensure contiguity for IOMMU compatibility
        
        Args:
            audio_data: Raw audio as int16 numpy array
        
        Returns:
            Preprocessed float32 audio, contiguous, 480,000 samples
        """
        # Define fixed shape requirement (30 seconds at 16kHz)
        fixed_samples = 480_000
        
        # Convert int16 to float32 (-1.0 to 1.0 range)
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Pad or truncate to fixed size
        if len(audio_float) < fixed_samples:
            # Pad with zeros (silence)
            audio_padded = np.pad(
                audio_float,
                (0, fixed_samples - len(audio_float)),
                mode='constant',
                constant_values=0.0
            )
            logger.debug(
                f"Padded audio from {len(audio_float)} to {fixed_samples} samples"
            )
        else:
            # Truncate to fixed size
            audio_padded = audio_float[:fixed_samples]
            logger.debug(
                f"Truncated audio from {len(audio_float)} to {fixed_samples} samples"
            )
        
        # Ensure contiguity for DMA/IOMMU
        audio_contiguous = np.ascontiguousarray(audio_padded)
        
        logger.info(
            f"Preprocessed audio: shape={audio_contiguous.shape}, "
            f"dtype={audio_contiguous.dtype}, contiguous={audio_contiguous.flags['C_CONTIGUOUS']}"
        )
        
        return audio_contiguous
