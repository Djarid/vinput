# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 Jason Huxley
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Unit tests for input_engine.py
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from src.input_engine import VirtualXboxController


class TestVirtualXboxController:
    """Test suite for VirtualXboxController class."""
    
    def test_initialization(self):
        """Test controller initialization."""
        controller = VirtualXboxController()
        
        assert controller.ui is None
        assert controller.is_initialized is False
    
    def test_initialize_success(self, mock_uinput):
        """Test successful controller initialization."""
        controller = VirtualXboxController()
        
        controller.initialize()
        
        assert controller.is_initialized is True
        assert controller.ui is not None
    
    def test_initialize_permission_error(self):
        """Test initialization with permission error."""
        with patch('evdev.UInput', side_effect=PermissionError("Access denied")):
            controller = VirtualXboxController()
            
            with pytest.raises(PermissionError):
                controller.initialize()
    
    def test_shutdown(self, mock_uinput):
        """Test controller shutdown."""
        controller = VirtualXboxController()
        controller.initialize()
        
        controller.shutdown()
        
        assert controller.is_initialized is False
        mock_uinput.close.assert_called_once()
    
    def test_shutdown_without_initialize(self):
        """Test shutdown without initialization."""
        controller = VirtualXboxController()
        
        # Should not raise exception
        controller.shutdown()
        assert controller.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_tap_button(self, mock_uinput):
        """Test button tap action."""
        controller = VirtualXboxController()
        controller.initialize()
        
        await controller.tap_button('A', duration_ms=50)
        
        # Verify button press and release
        assert mock_uinput.write.call_count >= 2
        assert mock_uinput.syn.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_tap_button_various_buttons(self, mock_uinput):
        """Test tapping different buttons."""
        controller = VirtualXboxController()
        controller.initialize()
        
        buttons = ['A', 'B', 'X', 'Y', 'LB', 'RB', 'Start', 'Back']
        
        for button in buttons:
            await controller.tap_button(button, duration_ms=10)
            assert mock_uinput.write.called
    
    @pytest.mark.asyncio
    async def test_tap_button_invalid(self, mock_uinput):
        """Test tapping invalid button raises error."""
        controller = VirtualXboxController()
        controller.initialize()
        
        with pytest.raises(ValueError, match="Unknown button"):
            await controller.tap_button('InvalidButton')
    
    @pytest.mark.asyncio
    async def test_tap_button_without_initialization(self):
        """Test tapping button without initialization."""
        controller = VirtualXboxController()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await controller.tap_button('A')
    
    @pytest.mark.asyncio
    async def test_move_stick(self, mock_uinput):
        """Test stick movement."""
        controller = VirtualXboxController()
        controller.initialize()
        
        await controller.move_stick('left', x=32767, y=-32768, duration_ms=100)
        
        # Verify axis writes
        assert mock_uinput.write.called
        assert mock_uinput.syn.called
    
    @pytest.mark.asyncio
    async def test_move_stick_both_sticks(self, mock_uinput):
        """Test moving both left and right sticks."""
        controller = VirtualXboxController()
        controller.initialize()
        
        # Left stick
        await controller.move_stick('left', x=10000, y=20000, duration_ms=50)
        
        # Right stick
        await controller.move_stick('right', x=-10000, y=-20000, duration_ms=50)
        
        assert mock_uinput.write.call_count >= 4  # At least 2 writes per stick
    
    @pytest.mark.asyncio
    async def test_move_stick_invalid(self, mock_uinput):
        """Test moving invalid stick raises error."""
        controller = VirtualXboxController()
        controller.initialize()
        
        with pytest.raises(ValueError, match="Unknown stick"):
            await controller.move_stick('middle', x=0, y=0)
    
    @pytest.mark.asyncio
    async def test_move_stick_range_validation(self, mock_uinput):
        """Test stick movement with out-of-range values."""
        controller = VirtualXboxController()
        controller.initialize()
        
        # Values should be clamped to valid range
        await controller.move_stick('left', x=99999, y=-99999, duration_ms=50)
        
        # Should not raise exception
        assert mock_uinput.write.called
    
    @pytest.mark.asyncio
    async def test_move_trigger(self, mock_uinput):
        """Test trigger movement."""
        controller = VirtualXboxController()
        controller.initialize()
        
        await controller.move_trigger('left', value=128)
        
        assert mock_uinput.write.called
        assert mock_uinput.syn.called
    
    @pytest.mark.asyncio
    async def test_move_trigger_both(self, mock_uinput):
        """Test both left and right triggers."""
        controller = VirtualXboxController()
        controller.initialize()
        
        await controller.move_trigger('left', value=255)
        await controller.move_trigger('right', value=128)
        
        assert mock_uinput.write.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_move_trigger_invalid(self, mock_uinput):
        """Test moving invalid trigger raises error."""
        controller = VirtualXboxController()
        controller.initialize()
        
        with pytest.raises(ValueError, match="Unknown trigger"):
            await controller.move_trigger('middle', value=128)
    
    @pytest.mark.asyncio
    async def test_move_dpad(self, mock_uinput):
        """Test D-pad movement."""
        controller = VirtualXboxController()
        controller.initialize()
        
        directions = ['up', 'down', 'left', 'right']
        
        for direction in directions:
            await controller.move_dpad(direction)
            assert mock_uinput.write.called
    
    @pytest.mark.asyncio
    async def test_move_dpad_invalid(self, mock_uinput):
        """Test moving D-pad in invalid direction."""
        controller = VirtualXboxController()
        controller.initialize()
        
        with pytest.raises(ValueError, match="Unknown direction"):
            await controller.move_dpad('diagonal')
    
    @pytest.mark.asyncio
    async def test_button_duration_timing(self, mock_uinput):
        """Test that button press respects duration."""
        controller = VirtualXboxController()
        controller.initialize()
        
        import time
        start = time.time()
        await controller.tap_button('A', duration_ms=100)
        elapsed = (time.time() - start) * 1000
        
        # Should take at least 100ms
        assert elapsed >= 95  # Allow small margin for timing
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_uinput):
        """Test controller can be used as context manager."""
        async with VirtualXboxController() as controller:
            controller.initialize()
            await controller.tap_button('A', duration_ms=50)
            assert controller.is_initialized is True
        
        # Should be cleaned up after context
        # (Note: Would need to implement __aenter__/__aexit__ for this to work)
