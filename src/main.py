# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Main orchestrator for vinput.
Coordinates audio capture, inference, and input emulation in an async pipeline.
"""

import asyncio
import logging
import yaml
import os
from typing import Optional, Dict, Callable
from concurrent.futures import ThreadPoolExecutor

from src.audio_engine import AudioEngine
from src.inference_engine import WhisperNPU
from src.input_engine import VirtualXboxController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VinputOrchestrator:
    """
    Orchestrates the voice-to-input pipeline:
    Audio Capture → VAD → Preprocessing → Inference → Command Parsing → uinput Events
    """

    def __init__(
        self,
        encoder_model_path: str,
        decoder_model_path: str,
        vaip_config_path: str,
        commands_yaml_path: str,
        sample_rate: int = 16000,
    ):
        """
        Initialize the orchestrator.

        Args:
            encoder_model_path: Path to Whisper encoder ONNX model
            decoder_model_path: Path to Whisper decoder ONNX model
            vaip_config_path: Path to vaip_config.json
            commands_yaml_path: Path to commands.yaml
            sample_rate: Audio sample rate
        """
        self.encoder_model_path = encoder_model_path
        self.decoder_model_path = decoder_model_path
        self.vaip_config_path = vaip_config_path
        self.sample_rate = sample_rate
        
        # Initialize components
        self.audio_engine = AudioEngine(sample_rate=sample_rate)
        self.inference_engine = WhisperNPU(
            encoder_model_path=encoder_model_path,
            decoder_model_path=decoder_model_path,
            vaip_config_path=vaip_config_path,
        )
        self.controller = VirtualXboxController()
        
        # Load command mappings
        self.commands = self._load_commands(commands_yaml_path)
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info("VinputOrchestrator initialized")

    def _load_commands(self, yaml_path: str) -> Dict[str, Callable]:
        """
        Load voice command mappings from YAML.

        Args:
            yaml_path: Path to commands.yaml

        Returns:
            Dictionary mapping command strings to callable handlers
        """
        if not os.path.exists(yaml_path):
            logger.warning(f"Commands file not found: {yaml_path}")
            return {}
        
        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            commands = {}
            for cmd_name, cmd_action in config.get('commands', {}).items():
                # For now, store the raw action; in production, map to actual callables
                commands[cmd_name.lower()] = cmd_action
            
            logger.info(f"Loaded {len(commands)} commands from {yaml_path}")
            return commands
        except Exception as e:
            logger.error(f"Failed to load commands: {e}")
            return {}

    async def _execute_command(self, command_text: str) -> None:
        """
        Parse transcribed text and execute corresponding command.

        Args:
            command_text: Transcribed text from Whisper
        """
        command_text_lower = command_text.lower().strip()
        
        # Exact match
        if command_text_lower in self.commands:
            action = self.commands[command_text_lower]
            await self._execute_action(action)
            return
        
        # Partial match
        for cmd_name, action in self.commands.items():
            if cmd_name in command_text_lower:
                logger.info(f"Matched command: {cmd_name}")
                await self._execute_action(action)
                return
        
        logger.warning(f"No command matched: '{command_text}'")

    async def _execute_action(self, action: Dict) -> None:
        """
        Execute a single action (button press, stick move, etc.).

        Args:
            action: Action dictionary from commands.yaml
        """
        try:
            action_type = action.get('type')
            
            if action_type == 'button':
                button = action.get('button')
                duration = action.get('duration', 50)
                await self.controller.tap_button(button, duration_ms=duration)
            
            elif action_type == 'button_hold':
                button = action.get('button')
                duration = action.get('duration', 1000)
                await self.controller.hold_button(button, duration_ms=duration)
            
            elif action_type == 'stick':
                stick = action.get('stick')
                x = action.get('x', 0)
                y = action.get('y', 0)
                duration = action.get('duration', 500)
                await self.controller.move_stick(stick, x, y, duration_ms=duration)
            
            elif action_type == 'trigger':
                trigger = action.get('trigger')
                value = action.get('value', 255)
                await self.controller.move_trigger(trigger, value=value)
            
            elif action_type == 'dpad':
                direction = action.get('direction')
                await self.controller.move_dpad(direction)
            
            elif action_type == 'sequence':
                # Execute multiple actions in sequence
                for sub_action in action.get('actions', []):
                    await self._execute_action(sub_action)
                    await asyncio.sleep(0.1)  # Small delay between actions
            
            else:
                logger.warning(f"Unknown action type: {action_type}")
        
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")

    async def process_audio_loop(self) -> None:
        """
        Main audio processing loop.
        Continuously listens for speech and transcribes commands.
        """
        try:
            while True:
                try:
                    logger.info("Listening for speech...")
                    
                    # Detect speech and accumulate audio
                    audio_data = await self.audio_engine.detect_speech(buffer_ms=500)
                    
                    if len(audio_data) == 0:
                        logger.debug("No audio detected")
                        continue
                    
                    # Preprocess audio
                    audio_preprocessed = await self.audio_engine.preprocess_audio(audio_data)
                    
                    # Run inference in thread pool to prevent blocking
                    loop = asyncio.get_event_loop()
                    text = await loop.run_in_executor(
                        self.executor,
                        self.inference_engine.transcribe,
                        audio_preprocessed
                    )
                    
                    # Wait for the async version
                    # Since transcribe is async, we need to run it properly
                    if asyncio.iscoroutine(text):
                        text = await text
                    
                    logger.info(f"Transcription: '{text}'")
                    
                    # Execute command
                    await self._execute_command(text)
                    
                except asyncio.CancelledError:
                    logger.info("Audio loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in audio loop: {e}")
                    await asyncio.sleep(1)  # Brief delay before retrying
        
        finally:
            await self.audio_engine.stop()

    async def start(self) -> None:
        """
        Start the voice automation system.
        Initializes all components and starts the main loop.
        """
        try:
            logger.info("Starting vinput...")
            
            # Initialize controller
            self.controller.initialize()
            logger.info("Virtual controller initialized")
            
            # Initialize inference engine
            self.inference_engine.initialize()
            logger.info("Inference engine initialized")
            
            # Warm up NPU
            await self.inference_engine.warm_up()
            
            # Start audio capture
            await self.audio_engine.start()
            logger.info("Audio capture started")
            
            # Run main loop
            await self.process_audio_loop()
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """
        Gracefully shut down all components.
        """
        logger.info("Shutting down vinput...")
        
        try:
            await self.audio_engine.stop()
        except Exception as e:
            logger.error(f"Error stopping audio engine: {e}")
        
        try:
            self.controller.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down controller: {e}")
        
        try:
            self.inference_engine.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down inference engine: {e}")
        
        try:
            self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")
        
        logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    # Configuration paths (adjust as needed)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    encoder_model = os.path.join(base_dir, "models", "encoder_int8.onnx")
    decoder_model = os.path.join(base_dir, "models", "decoder_int8.onnx")
    vaip_config = os.path.join(base_dir, "config", "vaip_config.json")
    commands_yaml = os.path.join(base_dir, "config", "commands.yaml")
    
    # Create orchestrator
    orchestrator = VinputOrchestrator(
        encoder_model_path=encoder_model,
        decoder_model_path=decoder_model,
        vaip_config_path=vaip_config,
        commands_yaml_path=commands_yaml,
    )
    
    # Start the system
    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
