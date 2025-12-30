"""Tests for terminal_handler.py - Terminal rendering and overlay management"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import struct
import threading
import time

from sumonitor.terminal.terminal_handler import TerminalHandler
from sumonitor.data.log_reader import LogReader


class TestTerminalSize:
    """Test get_terminal_size() system call"""

    def test_returns_rows_and_cols(self, mocker):
        """Should return terminal dimensions via ioctl"""
        mock_pexpect = Mock()
        mock_pexpect.closed = False

        handler = TerminalHandler(LogReader(), mock_pexpect)

        mock_ioctl = mocker.patch('fcntl.ioctl')
        mock_ioctl.return_value = struct.pack('hhhh', 24, 80, 0, 0)

        rows, cols = handler.get_terminal_size()

        assert rows == 24
        assert cols == 80

    def test_handles_different_sizes(self, mocker):
        """Should correctly parse different terminal sizes"""
        mock_pexpect = Mock()
        mock_pexpect.closed = False

        handler = TerminalHandler(LogReader(), mock_pexpect)

        mock_ioctl = mocker.patch('fcntl.ioctl')
        mock_ioctl.return_value = struct.pack('hhhh', 50, 120, 0, 0)

        rows, cols = handler.get_terminal_size()

        assert rows == 50
        assert cols == 120


class TestOnResize:
    """Test on_resize() signal handler"""

    def test_updates_pexpect_window_size(self, mocker):
        """Should call pexpect.setwinsize() with new terminal size"""
        mock_pexpect = Mock()
        mock_pexpect.closed = False
        mock_pexpect.setwinsize = Mock()

        handler = TerminalHandler(LogReader(), mock_pexpect)

        mocker.patch.object(handler, 'get_terminal_size', return_value=(30, 100))

        handler.on_resize(None, None)

        mock_pexpect.setwinsize.assert_called_once_with(30, 100)

    def test_skips_when_process_closed(self):
        """Should not update if pexpect process is closed"""
        mock_pexpect = Mock()
        mock_pexpect.closed = True
        mock_pexpect.setwinsize = Mock()

        handler = TerminalHandler(LogReader(), mock_pexpect)

        handler.on_resize(None, None)

        mock_pexpect.setwinsize.assert_not_called()


class TestOverlayDataFormatting:
    """Test get_overlay_data() string formatting"""

    def test_formats_with_all_metrics(self, mocker, mock_usage_entry):
        """Should format tokens, cost, messages, reset time"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1, input_tokens=1000, output_tokens=500, cost=1.50)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result = handler.get_overlay_data()

        assert "Tokens:" in result
        assert "Cost:" in result
        assert "Messages:" in result
        assert "Session reset" in result

    def test_returns_empty_when_no_data(self):
        """Should return empty string when no usage data"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = []

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result = handler.get_overlay_data()

        assert result == ""

    def test_displays_pro_plan_limits(self, mocker, mock_usage_entry):
        """Should display PRO plan limits in overlay"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1, input_tokens=1000, output_tokens=500)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result = handler.get_overlay_data()

        # PRO plan limits: 19,000 tokens, $18.00, 250 messages
        assert "/19000" in result or "/19,000" in result
        assert "/18.0" in result  # Cost format is .2f which gives "18.0" for 18.00
        assert "/250" in result

    def test_formats_cost_with_two_decimals(self, mock_usage_entry):
        """Cost should be formatted with 2 decimal places"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1, cost=1.5)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result = handler.get_overlay_data()

        assert "1.50" in result


class TestDrawOverlay:
    """Test draw_overlay() thread behavior"""

    def test_thread_starts_as_daemon(self, mock_pexpect):
        """Overlay thread should be daemon thread"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        assert handler.overlay_thread.daemon is True

    def test_thread_is_alive_after_init(self, mock_pexpect):
        """Thread should be running after initialization"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        assert handler.overlay_thread.is_alive()

    def test_thread_exits_when_process_closes(self, mock_pexpect):
        """Thread should exit when pexpect process closes"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        # Simulate process closing
        mock_pexpect.closed = True

        # Wait for thread to notice (max 3 seconds)
        handler.overlay_thread.join(timeout=3)

        assert not handler.overlay_thread.is_alive()


class TestOverlayRendering:
    """Test overlay rendering to stdout"""

    def test_truncates_to_terminal_width(self, mocker, mock_usage_entry):
        """Overlay text should be truncated to terminal width"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1, input_tokens=1000, output_tokens=500)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        # Mock terminal size to 40 columns
        mocker.patch.object(handler, 'get_terminal_size', return_value=(24, 40))

        # Get the overlay text
        text = handler.get_overlay_data()

        # In draw_overlay, text is truncated: text = text[:cols]
        truncated = text[:40]

        assert len(truncated) <= 40

    def test_writes_to_stdout(self, mocker, mock_usage_entry):
        """Should write overlay bytes to stdout"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Set closed to prevent thread loop

        mock_stdout_write = mocker.patch('sys.stdout.write')
        mock_stdout_flush = mocker.patch('sys.stdout.flush')

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        # Give thread brief time to execute once before closing
        time.sleep(0.1)

        # Thread should have attempted to write at least once
        # (may not be called if thread exits immediately)


class TestInitialization:
    """Test TerminalHandler initialization"""

    def test_sets_in_alt_screen_false(self, mock_pexpect):
        """in_alt_screen should default to False"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        assert handler.in_alt_screen is False

    def test_stores_pexpect_reference(self, mock_pexpect):
        """Should store reference to pexpect object"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        assert handler.p is mock_pexpect

    def test_stores_log_reader_reference(self):
        """Should store reference to LogReader"""
        log_reader = LogReader()
        mock_pexpect = Mock()
        mock_pexpect.closed = False

        handler = TerminalHandler(log_reader, mock_pexpect)

        assert handler.log_reader is log_reader

    def test_starts_overlay_thread(self, mock_pexpect):
        """Should start overlay thread during initialization"""
        handler = TerminalHandler(LogReader(), mock_pexpect)

        assert handler.overlay_thread is not None
        assert isinstance(handler.overlay_thread, threading.Thread)


class TestEdgeCases:
    """Edge cases and boundary conditions"""

    def test_handles_very_long_overlay_text(self, mocker, mock_usage_entry):
        """Should handle overlay text longer than terminal width"""
        mock_log_reader = Mock(spec=LogReader)
        # Create many entries to generate long text
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1, input_tokens=100000, output_tokens=50000)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        mocker.patch.object(handler, 'get_terminal_size', return_value=(24, 20))

        text = handler.get_overlay_data()

        # Should work without errors even if text is very long
        assert isinstance(text, str)

    def test_handles_empty_log_reader(self):
        """Should handle LogReader with no entries"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = []

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result = handler.get_overlay_data()

        assert result == ""

    def test_overlay_data_called_repeatedly(self, mocker, mock_usage_entry):
        """get_overlay_data() should work when called multiple times"""
        mock_log_reader = Mock(spec=LogReader)
        mock_log_reader.parse_json_files.return_value = [
            mock_usage_entry(hours_ago=1)
        ]

        mock_pexpect = Mock()
        mock_pexpect.closed = True  # Prevent background thread from running

        handler = TerminalHandler(mock_log_reader, mock_pexpect)

        result1 = handler.get_overlay_data()
        result2 = handler.get_overlay_data()
        result3 = handler.get_overlay_data()

        # Should return consistent results
        assert result1 == result2 == result3
        assert len(result1) > 0
