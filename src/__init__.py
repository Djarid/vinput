"""
Package initialization for vinput.
Exposes main classes for easy importing.
"""

from src.audio_engine import AudioEngine
from src.inference_engine import WhisperNPU
from src.input_engine import VirtualXboxController

__version__ = "0.1.0"
__author__ = "vinput contributors"

__all__ = [
    "AudioEngine",
    "WhisperNPU",
    "VirtualXboxController",
]
