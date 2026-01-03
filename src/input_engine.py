# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Input engine for vinput.
Creates virtual Xbox 360 controller via uinput for Wayland automation.
"""

import asyncio
import logging
from typing import Optional, Dict
from evdev import uinput, ecodes, AbsInfo

logger = logging.getLogger(__name__)


class VirtualXboxController:
    """
    Emulates an Xbox 360 controller via uinput.
    Allows voice commands to control games and applications on Wayland.
    """

    # Xbox 360 Controller IDs
    VENDOR_ID = 0x045e  # Microsoft
    PRODUCT_ID = 0x028e  # Xbox 360 Controller

    def __init__(self):
        """Initialize the virtual Xbox 360 controller."""
        self.ui = None
        self._is_initialized = False
        logger.info("VirtualXboxController instantiated")

    def initialize(self) -> None:
        """
        Initialize the uinput device with Xbox 360 controller capabilities.
        Must be called before any button/axis operations.
        """
        if self._is_initialized:
            logger.warning("Virtual controller already initialized")
            return

        try:
            # Define button capabilities
            buttons = {
                ecodes.BTN_SOUTH: None,      # A
                ecodes.BTN_EAST: None,       # B
                ecodes.BTN_NORTH: None,      # X
                ecodes.BTN_WEST: None,       # Y
                ecodes.BTN_TL: None,         # LB
                ecodes.BTN_TR: None,         # RB
                ecodes.BTN_SELECT: None,     # Back
                ecodes.BTN_START: None,      # Start
                ecodes.BTN_MODE: None,       # Guide
                ecodes.BTN_THUMBL: None,     # L3 (left stick press)
                ecodes.BTN_THUMBR: None,     # R3 (right stick press)
            }

            # Define axis capabilities with proper Xbox ranges
            axes = {
                ecodes.ABS_X: AbsInfo(
                    value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=1
                ),  # Left stick X
                ecodes.ABS_Y: AbsInfo(
                    value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=1
                ),  # Left stick Y
                ecodes.ABS_RX: AbsInfo(
                    value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=1
                ),  # Right stick X
                ecodes.ABS_RY: AbsInfo(
                    value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=1
                ),  # Right stick Y
                ecodes.ABS_Z: AbsInfo(
                    value=0, min=0, max=255, fuzz=0, flat=0, resolution=1
                ),  # Left trigger
                ecodes.ABS_RZ: AbsInfo(
                    value=0, min=0, max=255, fuzz=0, flat=0, resolution=1
                ),  # Right trigger
                ecodes.ABS_HAT0X: AbsInfo(
                    value=0, min=-1, max=1, fuzz=0, flat=0, resolution=1
                ),  # D-Pad X
                ecodes.ABS_HAT0Y: AbsInfo(
                    value=0, min=-1, max=1, fuzz=0, flat=0, resolution=1
                ),  # D-Pad Y
            }

            # Build capabilities dictionary
            capabilities = {
                ecodes.EV_KEY: buttons.keys(),
                ecodes.EV_ABS: axes,
            }

            # Create uinput device
            self.ui = uinput.UInput(
                events=capabilities,
                name="Virtual Xbox 360 Controller",
                vendor=self.VENDOR_ID,
                product=self.PRODUCT_ID,
                version=0x0100,
            )

            self._is_initialized = True
            logger.info("Virtual Xbox 360 controller initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize virtual controller: {e}")
            raise

    def _ensure_initialized(self) -> None:
        """Verify the controller is initialized before use."""
        if not self._is_initialized or not self.ui:
            raise RuntimeError(
                "Virtual controller not initialized. Call initialize() first."
            )

    async def tap_button(self, button_name: str, duration_ms: int = 50) -> None:
        """
        Press and release a button.

        Args:
            button_name: Button name (e.g., 'A', 'B', 'X', 'Y', 'LB', 'RB', etc.)
            duration_ms: Press duration in milliseconds
        """
        self._ensure_initialized()

        button_map = {
            'A': ecodes.BTN_SOUTH,
            'B': ecodes.BTN_EAST,
            'X': ecodes.BTN_NORTH,
            'Y': ecodes.BTN_WEST,
            'LB': ecodes.BTN_TL,
            'RB': ecodes.BTN_TR,
            'Back': ecodes.BTN_SELECT,
            'Start': ecodes.BTN_START,
            'Guide': ecodes.BTN_MODE,
            'L3': ecodes.BTN_THUMBL,
            'R3': ecodes.BTN_THUMBR,
        }

        if button_name not in button_map:
            logger.error(f"Unknown button: {button_name}")
            raise ValueError(f"Unknown button: {button_name}")

        button_code = button_map[button_name]

        try:
            # Press
            self.ui.write(ecodes.EV_KEY, button_code, 1)
            self.ui.syn()
            
            # Wait
            await asyncio.sleep(duration_ms / 1000.0)
            
            # Release
            self.ui.write(ecodes.EV_KEY, button_code, 0)
            self.ui.syn()
            
            logger.debug(f"Tapped button: {button_name}")
        except Exception as e:
            logger.error(f"Failed to tap button {button_name}: {e}")
            raise

    async def hold_button(self, button_name: str, duration_ms: int = 1000) -> None:
        """
        Hold a button for a specified duration.

        Args:
            button_name: Button name
            duration_ms: Hold duration in milliseconds
        """
        self._ensure_initialized()

        button_map = {
            'A': ecodes.BTN_SOUTH,
            'B': ecodes.BTN_EAST,
            'X': ecodes.BTN_NORTH,
            'Y': ecodes.BTN_WEST,
            'LB': ecodes.BTN_TL,
            'RB': ecodes.BTN_TR,
            'Back': ecodes.BTN_SELECT,
            'Start': ecodes.BTN_START,
            'Guide': ecodes.BTN_MODE,
            'L3': ecodes.BTN_THUMBL,
            'R3': ecodes.BTN_THUMBR,
        }

        if button_name not in button_map:
            raise ValueError(f"Unknown button: {button_name}")

        button_code = button_map[button_name]

        try:
            # Press
            self.ui.write(ecodes.EV_KEY, button_code, 1)
            self.ui.syn()
            
            # Wait
            await asyncio.sleep(duration_ms / 1000.0)
            
            # Release
            self.ui.write(ecodes.EV_KEY, button_code, 0)
            self.ui.syn()
            
            logger.debug(f"Held button: {button_name} for {duration_ms}ms")
        except Exception as e:
            logger.error(f"Failed to hold button {button_name}: {e}")
            raise

    async def move_stick(
        self, stick_name: str, x: int, y: int, duration_ms: int = 500
    ) -> None:
        """
        Move a stick to a position and hold for a duration.

        Args:
            stick_name: 'left' or 'right'
            x: X position (-32768 to 32767)
            y: Y position (-32768 to 32767)
            duration_ms: Duration to hold the position
        """
        self._ensure_initialized()

        stick_map = {
            'left': (ecodes.ABS_X, ecodes.ABS_Y),
            'right': (ecodes.ABS_RX, ecodes.ABS_RY),
        }

        if stick_name not in stick_map:
            raise ValueError(f"Unknown stick: {stick_name}")

        abs_x, abs_y = stick_map[stick_name]

        try:
            # Move stick
            self.ui.write(ecodes.EV_ABS, abs_x, x)
            self.ui.write(ecodes.EV_ABS, abs_y, y)
            self.ui.syn()
            
            # Wait
            await asyncio.sleep(duration_ms / 1000.0)
            
            # Return to center
            self.ui.write(ecodes.EV_ABS, abs_x, 0)
            self.ui.write(ecodes.EV_ABS, abs_y, 0)
            self.ui.syn()
            
            logger.debug(
                f"Moved {stick_name} stick to ({x}, {y}) for {duration_ms}ms"
            )
        except Exception as e:
            logger.error(f"Failed to move {stick_name} stick: {e}")
            raise

    async def move_trigger(self, trigger_name: str, value: int = 255) -> None:
        """
        Activate a trigger.

        Args:
            trigger_name: 'left' or 'right'
            value: Trigger value (0-255)
        """
        self._ensure_initialized()

        trigger_map = {
            'left': ecodes.ABS_Z,
            'right': ecodes.ABS_RZ,
        }

        if trigger_name not in trigger_map:
            raise ValueError(f"Unknown trigger: {trigger_name}")

        if not 0 <= value <= 255:
            raise ValueError(f"Trigger value must be 0-255, got {value}")

        trigger_code = trigger_map[trigger_name]

        try:
            self.ui.write(ecodes.EV_ABS, trigger_code, value)
            self.ui.syn()
            logger.debug(f"Set {trigger_name} trigger to {value}")
        except Exception as e:
            logger.error(f"Failed to set {trigger_name} trigger: {e}")
            raise

    async def move_dpad(self, direction: str) -> None:
        """
        Move the D-Pad.

        Args:
            direction: 'up', 'down', 'left', 'right', 'up-left', 'up-right', 
                      'down-left', 'down-right', or 'center'
        """
        self._ensure_initialized()

        direction_map = {
            'up': (0, -1),
            'down': (0, 1),
            'left': (-1, 0),
            'right': (1, 0),
            'up-left': (-1, -1),
            'up-right': (1, -1),
            'down-left': (-1, 1),
            'down-right': (1, 1),
            'center': (0, 0),
        }

        if direction not in direction_map:
            raise ValueError(f"Unknown direction: {direction}")

        x, y = direction_map[direction]

        try:
            self.ui.write(ecodes.EV_ABS, ecodes.ABS_HAT0X, x)
            self.ui.write(ecodes.EV_ABS, ecodes.ABS_HAT0Y, y)
            self.ui.syn()
            logger.debug(f"D-Pad moved to: {direction}")
        except Exception as e:
            logger.error(f"Failed to move D-Pad: {e}")
            raise

    def shutdown(self) -> None:
        """Clean up and close the uinput device."""
        if self.ui:
            try:
                self.ui.close()
                logger.info("Virtual controller closed")
            except Exception as e:
                logger.error(f"Error closing virtual controller: {e}")
        self._is_initialized = False
