"""Tests for helper utilities."""

import pytest
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
import os
import asyncio
from ptop.utils.helpers import (
    read_proc_file,
    parse_proc_stat_line,
    calculate_cpu_percentage,
    parse_meminfo,
    get_process_list,
    run_command
)


class TestReadProcFile:
    """Test read_proc_file function."""
    
    def test_read_proc_file_success(self):
        """Test successful file reading."""
        mock_content = "test content\n"
        with patch("builtins.open", mock_open(read_data=mock_content)):
            result = read_proc_file("/proc/test")
            assert result == "test content"
    
    def test_read_proc_file_ioerror(self):
        """Test IOError handling."""
        with patch("builtins.open", side_effect=IOError("File not found")):
            result = read_proc_file("/proc/nonexistent")
            assert result is None
    
    def test_read_proc_file_oserror(self):
        """Test OSError handling."""
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = read_proc_file("/proc/restricted")
            assert result is None
    
    def test_read_proc_file_permission_error(self):
        """Test PermissionError handling."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = read_proc_file("/proc/protected")
            assert result is None


class TestParseProcStatLine:
    """Test parse_proc_stat_line function."""
    
    def test_parse_proc_stat_line_complete(self):
        """Test parsing complete stat line."""
        line = "cpu  123 456 789 1011 1213 1415 1617 1819 2021 2223"
        result = parse_proc_stat_line(line)
        expected = {
            'user': 123,
            'nice': 456,
            'system': 789,
            'idle': 1011,
            'iowait': 1213,
            'irq': 1415,
            'softirq': 1617,
            'steal': 1819,
            'guest': 2021,
            'guest_nice': 2223,
        }
        assert result == expected
    
    def test_parse_proc_stat_line_minimal(self):
        """Test parsing minimal stat line (7 fields)."""
        line = "cpu  123 456 789 1011 1213 1415 1617"
        result = parse_proc_stat_line(line)
        expected = {
            'user': 123,
            'nice': 456,
            'system': 789,
            'idle': 1011,
            'iowait': 1213,
            'irq': 1415,
            'softirq': 1617,
            'steal': 0,
            'guest': 0,
            'guest_nice': 0,
        }
        assert result == expected
    
    def test_parse_proc_stat_line_insufficient_fields(self):
        """Test parsing stat line with insufficient fields."""
        line = "cpu  123 456"
        result = parse_proc_stat_line(line)
        assert result == {}
    
    def test_parse_proc_stat_line_with_8_fields(self):
        """Test parsing stat line with 8 fields."""
        line = "cpu  123 456 789 1011 1213 1415 1617 1819"
        result = parse_proc_stat_line(line)
        expected = {
            'user': 123,
            'nice': 456,
            'system': 789,
            'idle': 1011,
            'iowait': 1213,
            'irq': 1415,
            'softirq': 1617,
            'steal': 1819,
            'guest': 0,
            'guest_nice': 0,
        }
        assert result == expected


class TestCalculateCpuPercentage:
    """Test calculate_cpu_percentage function."""
    
    def test_calculate_cpu_percentage_normal(self):
        """Test normal CPU percentage calculation."""
        prev_times = {
            'user': 100, 'nice': 0, 'system': 50, 'idle': 850,
            'iowait': 0, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        curr_times = {
            'user': 120, 'nice': 0, 'system': 60, 'idle': 920,
            'iowait': 0, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        # Total diff: 100, idle diff: 70, used diff: 30
        # CPU percentage: 30/100 * 100 = 30.0%
        result = calculate_cpu_percentage(prev_times, curr_times)
        assert result == 30.0
    
    def test_calculate_cpu_percentage_with_iowait(self):
        """Test CPU percentage calculation with iowait."""
        prev_times = {
            'user': 100, 'nice': 0, 'system': 50, 'idle': 800,
            'iowait': 50, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        curr_times = {
            'user': 120, 'nice': 0, 'system': 60, 'idle': 860,
            'iowait': 60, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        # Total diff: 100, idle+iowait diff: 70, used diff: 30
        result = calculate_cpu_percentage(prev_times, curr_times)
        assert result == 30.0
    
    def test_calculate_cpu_percentage_no_change(self):
        """Test CPU percentage when no time has passed."""
        times = {
            'user': 100, 'nice': 0, 'system': 50, 'idle': 850,
            'iowait': 0, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        result = calculate_cpu_percentage(times, times)
        assert result == 0.0
    
    def test_calculate_cpu_percentage_empty_prev(self):
        """Test CPU percentage with empty previous times."""
        curr_times = {
            'user': 120, 'nice': 0, 'system': 60, 'idle': 920,
            'iowait': 0, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        result = calculate_cpu_percentage({}, curr_times)
        assert result == 0.0
    
    def test_calculate_cpu_percentage_empty_curr(self):
        """Test CPU percentage with empty current times."""
        prev_times = {
            'user': 100, 'nice': 0, 'system': 50, 'idle': 850,
            'iowait': 0, 'irq': 0, 'softirq': 0, 'steal': 0,
            'guest': 0, 'guest_nice': 0
        }
        result = calculate_cpu_percentage(prev_times, {})
        assert result == 0.0


class TestParseMeminfo:
    """Test parse_meminfo function."""
    
    def test_parse_meminfo_complete(self, mock_proc_meminfo):
        """Test parsing complete meminfo."""
        result = parse_meminfo(mock_proc_meminfo)
        
        expected_keys = [
            'MemTotal', 'MemFree', 'MemAvailable', 'Buffers', 'Cached',
            'SwapTotal', 'SwapFree', 'SwapCached', 'Active', 'Inactive',
            'Dirty', 'Writeback', 'Mapped', 'Shmem', 'Slab',
            'SReclaimable', 'SUnreclaim'
        ]
        
        for key in expected_keys:
            assert key in result
        
        # Check conversion from kB to bytes
        assert result['MemTotal'] == 16384000 * 1024
        assert result['MemFree'] == 8192000 * 1024
    
    def test_parse_meminfo_malformed_lines(self):
        """Test parsing meminfo with malformed lines."""
        content = """MemTotal:       16384000 kB
InvalidLine
MemFree:        8192000 kB
AnotherInvalidLine: no_number
Buffers:        512000 kB"""
        
        result = parse_meminfo(content)
        assert 'MemTotal' in result
        assert 'MemFree' in result
        assert 'Buffers' in result
        assert len(result) == 3  # Only valid lines parsed
    
    def test_parse_meminfo_no_kb_suffix(self):
        """Test parsing meminfo without kB suffix."""
        content = """MemTotal:       16384000
MemFree:        8192000"""
        
        result = parse_meminfo(content)
        # Should still convert assuming kB
        assert result['MemTotal'] == 16384000 * 1024
        assert result['MemFree'] == 8192000 * 1024


class TestGetProcessList:
    """Test get_process_list function."""
    
    def test_get_process_list_success(self):
        """Test successful process list retrieval."""
        mock_entries = ['1', '2', '123', 'self', 'thread-self', '456', 'cpuinfo']
        with patch('os.listdir', return_value=mock_entries):
            result = get_process_list()
            expected = [1, 2, 123, 456]  # Only numeric entries
            assert result == expected
    
    def test_get_process_list_oserror(self):
        """Test OSError handling."""
        with patch('os.listdir', side_effect=OSError("Permission denied")):
            result = get_process_list()
            assert result == []
    
    def test_get_process_list_empty(self):
        """Test empty proc directory."""
        with patch('os.listdir', return_value=[]):
            result = get_process_list()
            assert result == []


class TestRunCommand:
    """Test run_command function."""
    
    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test successful command execution."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await run_command(['echo', 'test'])
            assert result == "output"
    
    @pytest.mark.asyncio
    async def test_run_command_failure(self):
        """Test command execution failure."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"error")
        mock_process.returncode = 1
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await run_command(['false'])
            assert result is None
    
    @pytest.mark.asyncio
    async def test_run_command_exception(self):
        """Test command execution with exception."""
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Command failed")):
            result = await run_command(['nonexistent'])
            assert result is None
    
    @pytest.mark.asyncio
    async def test_run_command_with_output_decoding(self):
        """Test command output decoding."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"test\noutput\n", b""))
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await run_command(['echo', 'test'])
            assert result == "test\noutput"  # Stripped trailing newline