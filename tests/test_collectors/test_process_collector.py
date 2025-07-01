"""Tests for Process metrics collector."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import asyncio
import os

from ptop.collectors.process import ProcessCollector, ProcessInfo
from ptop.collectors.base import BaseCollector


class TestProcessInfo:
    """Test ProcessInfo container class."""
    
    def test_initialization(self):
        """Test ProcessInfo initialization."""
        process = ProcessInfo(1234)
        
        assert process.pid == 1234
        assert process.name == ""
        assert process.cmdline == ""
        assert process.state == ""
        assert process.ppid == 0
        assert process.cpu_percent == 0.0
        assert process.memory_percent == 0.0
        assert process.memory_rss == 0
        assert process.memory_vms == 0
        assert process.threads == 0
        assert process.create_time == 0
        assert process.user == ""
        assert process.nice == 0


class TestProcessCollector:
    """Test ProcessCollector class."""
    
    @pytest.fixture
    def process_collector(self):
        """Create a ProcessCollector instance for testing."""
        return ProcessCollector()
    
    def test_inheritance(self, process_collector):
        """Test that ProcessCollector inherits from BaseCollector."""
        assert isinstance(process_collector, BaseCollector)
    
    def test_name_property(self, process_collector):
        """Test collector name property."""
        assert process_collector.name == "process"
    
    def test_update_interval_property(self, process_collector):
        """Test update interval property."""
        assert process_collector.update_interval == 2.0
        assert isinstance(process_collector.update_interval, float)
    
    def test_initialization(self, process_collector):
        """Test collector initialization."""
        assert process_collector._previous_cpu_times == {}
        assert process_collector._previous_collect_time == 0.0
        assert process_collector._system_memory_total == 0
    
    @pytest.mark.asyncio
    async def test_collect_method_structure(self, process_collector, mock_process_list, 
                                          mock_process_stat, mock_process_status, 
                                          mock_proc_meminfo):
        """Test that collect method returns expected structure."""
        with patch('ptop.utils.helpers.get_process_list', return_value=mock_process_list):
            with patch('ptop.utils.helpers.read_proc_file') as mock_read:
                def mock_read_side_effect(path):
                    if path == '/proc/meminfo':
                        return mock_proc_meminfo
                    elif '/stat' in path:
                        return mock_process_stat
                    elif '/status' in path:
                        return mock_process_status
                    elif '/cmdline' in path:
                        return "test-process\x00--arg1\x00--arg2"
                    return None
                
                mock_read.side_effect = mock_read_side_effect
                
                with patch('os.stat') as mock_os_stat:
                    mock_stat_result = MagicMock()
                    mock_stat_result.st_uid = 1000
                    mock_os_stat.return_value = mock_stat_result
                    
                    result = await process_collector.collect()
                    
                    # Check that all main sections are present
                    assert isinstance(result, dict)
                    assert 'processes' in result
                    assert 'total_processes' in result
                    assert 'process_summary' in result
                    
                    # Check process summary structure
                    summary = result['process_summary']
                    assert 'running' in summary
                    assert 'sleeping' in summary
                    assert 'stopped' in summary
                    assert 'total_memory_usage' in summary
                    assert 'total_threads' in summary
                    assert 'avg_cpu_usage' in summary
    
    @pytest.mark.asyncio
    async def test_get_system_memory_total(self, process_collector, mock_proc_meminfo):
        """Test _get_system_memory_total method."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            await process_collector._get_system_memory_total()
            
            # Should extract MemTotal and convert to bytes
            assert process_collector._system_memory_total == 16384000 * 1024
    
    @pytest.mark.asyncio
    async def test_get_system_memory_total_empty_file(self, process_collector):
        """Test _get_system_memory_total with empty file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            await process_collector._get_system_memory_total()
            assert process_collector._system_memory_total == 0
    
    @pytest.mark.asyncio
    async def test_get_system_memory_total_malformed_data(self, process_collector):
        """Test _get_system_memory_total with malformed data."""
        malformed_meminfo = "invalid\ndata\nhere"
        with patch('ptop.utils.helpers.read_proc_file', return_value=malformed_meminfo):
            await process_collector._get_system_memory_total()
            assert process_collector._system_memory_total == 0
    
    @pytest.mark.asyncio
    async def test_get_process_info_success(self, process_collector, mock_process_stat, 
                                          mock_process_status):
        """Test successful process info collection."""
        process_collector._system_memory_total = 16777216000  # 16GB
        
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if '/stat' in path:
                    return mock_process_stat
                elif '/status' in path:
                    return mock_process_status
                elif '/cmdline' in path:
                    return "test-process\x00--arg1\x00--arg2"
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.stat') as mock_os_stat:
                mock_stat_result = MagicMock()
                mock_stat_result.st_uid = 1000
                mock_os_stat.return_value = mock_stat_result
                
                current_time = 123456.0
                result = await process_collector._get_process_info(123, current_time)
                
                assert result is not None
                assert result.pid == 123
                assert result.name == "test-process"
                assert result.cmdline == "test-process --arg1 --arg2"
                assert result.state == "S"
                assert result.ppid == 1
                assert result.user == "1000"
                assert result.threads == 1
    
    @pytest.mark.asyncio
    async def test_get_process_info_missing_files(self, process_collector):
        """Test process info collection when files are missing."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await process_collector._get_process_info(123, 123456.0)
            
            # Should still return a ProcessInfo object with default values
            assert result is not None
            assert result.pid == 123
            assert result.name == ""
            assert result.cmdline == ""
    
    @pytest.mark.asyncio
    async def test_get_process_info_permission_error(self, process_collector):
        """Test process info collection with permission error."""
        with patch('ptop.utils.helpers.read_proc_file', return_value="mock data"):
            with patch('os.stat', side_effect=PermissionError("Access denied")):
                result = await process_collector._get_process_info(123, 123456.0)
                
                assert result is not None
                assert result.user == "unknown"
    
    @pytest.mark.asyncio
    async def test_get_process_info_exception_handling(self, process_collector):
        """Test process info collection exception handling."""
        with patch('ptop.utils.helpers.read_proc_file', side_effect=Exception("Test error")):
            result = await process_collector._get_process_info(123, 123456.0)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_parse_stat_success(self, process_collector, mock_process_stat):
        """Test successful parsing of /proc/[pid]/stat."""
        process = ProcessInfo(123)
        current_time = 123456.0
        
        await process_collector._parse_stat(process, mock_process_stat, current_time)
        
        assert process.name == "test-process"
        assert process.state == "S"
        assert process.ppid == 1
        assert process.nice == 20
        assert process.threads == 1
        assert process.memory_rss > 0
        assert process.memory_vms > 0
    
    @pytest.mark.asyncio
    async def test_parse_stat_cpu_calculation_first_run(self, process_collector, mock_process_stat):
        """Test CPU calculation on first run (no previous data)."""
        process = ProcessInfo(123)
        current_time = 123456.0
        
        await process_collector._parse_stat(process, mock_process_stat, current_time)
        
        # First run should have 0% CPU
        assert process.cpu_percent == 0.0
        # But should store current times for next calculation
        assert 123 in process_collector._previous_cpu_times
    
    @pytest.mark.asyncio
    async def test_parse_stat_cpu_calculation_with_previous(self, process_collector, mock_process_stat):
        """Test CPU calculation with previous data."""
        process = ProcessInfo(123)
        current_time = 123456.0
        
        # Set up previous data
        process_collector._previous_cpu_times[123] = (100, 123400.0)  # Previous total time and timestamp
        process_collector._previous_collect_time = 123400.0
        
        # Mock stat data that shows some CPU time increase
        stat_with_more_cpu = "123 (test-process) S 1 123 123 0 -1 4194304 123 0 0 0 20 10 0 0 20 0 1 0 12345 1234567 100 18446744073709551615 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0 0"
        
        await process_collector._parse_stat(process, stat_with_more_cpu, current_time)
        
        # Should calculate some CPU percentage
        assert process.cpu_percent >= 0.0
    
    @pytest.mark.asyncio
    async def test_parse_stat_malformed_data(self, process_collector):
        """Test parsing malformed stat data."""
        process = ProcessInfo(123)
        malformed_stat = "123 incomplete"
        
        await process_collector._parse_stat(process, malformed_stat, 123456.0)
        
        # Should handle gracefully without crashing
        assert process.name == ""  # Should remain default
    
    @pytest.mark.asyncio
    async def test_parse_stat_memory_percentage_calculation(self, process_collector, mock_process_stat):
        """Test memory percentage calculation."""
        process = ProcessInfo(123)
        process_collector._system_memory_total = 16777216000  # 16GB
        
        await process_collector._parse_stat(process, mock_process_stat, 123456.0)
        
        # Should calculate memory percentage based on RSS and total memory
        assert process.memory_percent > 0.0
        assert process.memory_percent <= 100.0
    
    @pytest.mark.asyncio
    async def test_parse_status_success(self, process_collector, mock_process_status):
        """Test successful parsing of /proc/[pid]/status."""
        process = ProcessInfo(123)
        
        await process_collector._parse_status(process, mock_process_status)
        
        assert process.memory_rss == 12345 * 1024  # Convert from kB to bytes
        assert process.memory_vms == 123456 * 1024  # Convert from kB to bytes
        assert process.threads == 1
    
    @pytest.mark.asyncio
    async def test_parse_status_partial_data(self, process_collector):
        """Test parsing status with partial data."""
        process = ProcessInfo(123)
        partial_status = """Name:	test-process
State:	S (sleeping)
VmRSS:	12345 kB"""
        
        await process_collector._parse_status(process, partial_status)
        
        assert process.memory_rss == 12345 * 1024
        # Missing fields should remain default
        assert process.memory_vms == 0
        assert process.threads == 0
    
    @pytest.mark.asyncio
    async def test_parse_status_malformed_data(self, process_collector):
        """Test parsing malformed status data."""
        process = ProcessInfo(123)
        malformed_status = "invalid\ndata\nhere"
        
        await process_collector._parse_status(process, malformed_status)
        
        # Should handle gracefully
        assert process.memory_rss == 0
        assert process.memory_vms == 0
        assert process.threads == 0
    
    def test_get_process_summary_with_processes(self, process_collector):
        """Test process summary generation with processes."""
        processes = [
            ProcessInfo(1),
            ProcessInfo(2),
            ProcessInfo(3)
        ]
        
        # Set up different states
        processes[0].state = 'R'  # Running
        processes[0].memory_rss = 1000000
        processes[0].threads = 2
        processes[0].cpu_percent = 10.0
        
        processes[1].state = 'S'  # Sleeping
        processes[1].memory_rss = 2000000
        processes[1].threads = 1
        processes[1].cpu_percent = 5.0
        
        processes[2].state = 'Z'  # Zombie
        processes[2].memory_rss = 0
        processes[2].threads = 0
        processes[2].cpu_percent = 0.0
        
        summary = process_collector._get_process_summary(processes)
        
        assert summary['running'] == 1
        assert summary['sleeping'] == 1
        assert summary['stopped'] == 1
        assert summary['total_memory_usage'] == 3000000
        assert summary['total_threads'] == 3
        assert summary['avg_cpu_usage'] == 5.0  # (10+5+0)/3
    
    def test_get_process_summary_empty_list(self, process_collector):
        """Test process summary with empty process list."""
        summary = process_collector._get_process_summary([])
        assert summary == {}
    
    def test_get_process_summary_various_states(self, process_collector):
        """Test process summary with various process states."""
        processes = [
            ProcessInfo(1),
            ProcessInfo(2),
            ProcessInfo(3),
            ProcessInfo(4)
        ]
        
        processes[0].state = 'R'  # Running
        processes[1].state = 'S'  # Sleeping
        processes[2].state = 'T'  # Stopped
        processes[3].state = 'D'  # Uninterruptible sleep (not in summary categories)
        
        summary = process_collector._get_process_summary(processes)
        
        assert summary['running'] == 1
        assert summary['sleeping'] == 1
        assert summary['stopped'] == 1  # Only counts T and Z states
    
    @pytest.mark.asyncio
    async def test_collect_sorts_by_cpu_usage(self, process_collector, mock_process_list, 
                                            mock_process_stat, mock_process_status, 
                                            mock_proc_meminfo):
        """Test that collect sorts processes by CPU usage."""
        with patch('ptop.utils.helpers.get_process_list', return_value=[1, 2, 3]):
            with patch('ptop.utils.helpers.read_proc_file') as mock_read:
                def mock_read_side_effect(path):
                    if path == '/proc/meminfo':
                        return mock_proc_meminfo
                    elif '/stat' in path:
                        return mock_process_stat
                    elif '/status' in path:
                        return mock_process_status
                    elif '/cmdline' in path:
                        return "test-process"
                    return None
                
                mock_read.side_effect = mock_read_side_effect
                
                with patch('os.stat') as mock_os_stat:
                    mock_stat_result = MagicMock()
                    mock_stat_result.st_uid = 1000
                    mock_os_stat.return_value = mock_stat_result
                    
                    with patch.object(process_collector, '_get_process_info') as mock_get_info:
                        # Create processes with different CPU usage
                        process1 = ProcessInfo(1)
                        process1.cpu_percent = 10.0
                        process2 = ProcessInfo(2)
                        process2.cpu_percent = 30.0
                        process3 = ProcessInfo(3)
                        process3.cpu_percent = 20.0
                        
                        mock_get_info.side_effect = [process1, process2, process3]
                        
                        result = await process_collector.collect()
                        
                        # Should be sorted by CPU usage (descending)
                        processes = result['processes']
                        assert processes[0].cpu_percent == 30.0
                        assert processes[1].cpu_percent == 20.0
                        assert processes[2].cpu_percent == 10.0
    
    @pytest.mark.asyncio
    async def test_collect_limits_to_50_processes(self, process_collector):
        """Test that collect limits results to top 50 processes."""
        # Create a large list of process IDs
        large_process_list = list(range(1, 101))  # 100 processes
        
        with patch('ptop.utils.helpers.get_process_list', return_value=large_process_list):
            with patch('ptop.utils.helpers.read_proc_file') as mock_read:
                mock_read.return_value = "MemTotal: 16384000 kB"
                
                with patch.object(process_collector, '_get_process_info') as mock_get_info:
                    # Return a valid process for each PID
                    def create_process(pid, time):
                        process = ProcessInfo(pid)
                        process.cpu_percent = float(pid)  # Different CPU usage for each
                        return process
                    
                    mock_get_info.side_effect = create_process
                    
                    result = await process_collector.collect()
                    
                    # Should limit to 50 processes
                    assert len(result['processes']) == 50
                    assert result['total_processes'] == 100  # But total count should be correct
    
    @pytest.mark.asyncio
    async def test_collect_handles_disappeared_processes(self, process_collector, mock_proc_meminfo):
        """Test collect handles processes that disappear during collection."""
        with patch('ptop.utils.helpers.get_process_list', return_value=[1, 2, 3]):
            with patch('ptop.utils.helpers.read_proc_file') as mock_read:
                def mock_read_side_effect(path):
                    if path == '/proc/meminfo':
                        return mock_proc_meminfo
                    return None
                
                mock_read.side_effect = mock_read_side_effect
                
                with patch.object(process_collector, '_get_process_info') as mock_get_info:
                    # Simulate processes disappearing (return None for some)
                    process1 = ProcessInfo(1)
                    mock_get_info.side_effect = [
                        process1,  # PID 1 exists
                        None,      # PID 2 disappeared
                        OSError("No such process")  # PID 3 throws error
                    ]
                    
                    result = await process_collector.collect()
                    
                    # Should only include the successful process
                    assert len(result['processes']) == 1
                    assert result['processes'][0].pid == 1
                    assert result['total_processes'] == 3  # Original count
    
    @pytest.mark.asyncio
    async def test_full_collect_integration(self, process_collector, mock_process_list, 
                                          mock_process_stat, mock_process_status, 
                                          mock_proc_meminfo):
        """Test full collect method integration."""
        with patch('ptop.utils.helpers.get_process_list', return_value=mock_process_list):
            with patch('ptop.utils.helpers.read_proc_file') as mock_read:
                def mock_read_side_effect(path):
                    if path == '/proc/meminfo':
                        return mock_proc_meminfo
                    elif '/stat' in path:
                        return mock_process_stat
                    elif '/status' in path:
                        return mock_process_status
                    elif '/cmdline' in path:
                        return "test-process\x00--verbose"
                    return None
                
                mock_read.side_effect = mock_read_side_effect
                
                with patch('os.stat') as mock_os_stat:
                    mock_stat_result = MagicMock()
                    mock_stat_result.st_uid = 1000
                    mock_os_stat.return_value = mock_stat_result
                    
                    result = await process_collector.collect()
                    
                    # Verify structure
                    assert 'processes' in result
                    assert 'total_processes' in result
                    assert 'process_summary' in result
                    
                    # Check that we have processes
                    assert len(result['processes']) > 0
                    assert result['total_processes'] == len(mock_process_list)
                    
                    # Check process data quality
                    process = result['processes'][0]
                    assert process.pid > 0
                    assert process.name == "test-process"
                    assert "test-process --verbose" in process.cmdline
    
    @pytest.mark.asyncio
    async def test_collect_updates_previous_collect_time(self, process_collector, mock_process_list):
        """Test that collect updates the previous collect time."""
        initial_time = process_collector._previous_collect_time
        
        with patch('ptop.utils.helpers.get_process_list', return_value=mock_process_list):
            with patch('ptop.utils.helpers.read_proc_file', return_value="MemTotal: 16384000 kB"):
                with patch.object(process_collector, '_get_process_info', return_value=ProcessInfo(1)):
                    await process_collector.collect()
                    
                    # Should update the previous collect time
                    assert process_collector._previous_collect_time > initial_time
    
    @pytest.mark.asyncio
    async def test_collect_memory_initialization(self, process_collector, mock_process_list, mock_proc_meminfo):
        """Test that collect initializes system memory total if not set."""
        assert process_collector._system_memory_total == 0
        
        with patch('ptop.utils.helpers.get_process_list', return_value=mock_process_list):
            with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
                with patch.object(process_collector, '_get_process_info', return_value=ProcessInfo(1)):
                    await process_collector.collect()
                    
                    # Should have initialized system memory total
                    assert process_collector._system_memory_total > 0
    
    def test_process_collector_thread_safety(self, process_collector):
        """Test that multiple instances don't interfere with each other."""
        collector2 = ProcessCollector()
        
        # Set different state
        process_collector._system_memory_total = 1000000
        collector2._system_memory_total = 2000000
        
        # Each instance should maintain its own state
        assert process_collector._system_memory_total != collector2._system_memory_total
        assert process_collector._previous_cpu_times != collector2._previous_cpu_times
    
    @pytest.mark.asyncio
    async def test_edge_case_process_with_null_cmdline(self, process_collector):
        """Test handling process with null bytes in cmdline."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if '/cmdline' in path:
                    return "test\x00process\x00with\x00nulls\x00"
                elif '/stat' in path:
                    return "123 (test-process) S 1 123 123 0 -1 4194304 123 0 0 0 10 5 0 0 20 0 1 0 12345 1234567 100 18446744073709551615"
                return ""
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.stat') as mock_os_stat:
                mock_stat_result = MagicMock()
                mock_stat_result.st_uid = 1000
                mock_os_stat.return_value = mock_stat_result
                
                result = await process_collector._get_process_info(123, 123456.0)
                
                # Should replace null bytes with spaces
                assert result.cmdline == "test process with nulls"
    
    @pytest.mark.asyncio
    async def test_edge_case_very_large_process_list(self, process_collector):
        """Test handling very large process lists efficiently."""
        # Create a very large process list
        large_list = list(range(1, 1001))  # 1000 processes
        
        with patch('ptop.utils.helpers.get_process_list', return_value=large_list):
            with patch('ptop.utils.helpers.read_proc_file', return_value="MemTotal: 16384000 kB"):
                with patch.object(process_collector, '_get_process_info') as mock_get_info:
                    # Return a simple process for each
                    def create_simple_process(pid, time):
                        process = ProcessInfo(pid)
                        process.cpu_percent = 1.0
                        return process
                    
                    mock_get_info.side_effect = create_simple_process
                    
                    result = await process_collector.collect()
                    
                    # Should handle large lists but limit results
                    assert len(result['processes']) == 50
                    assert result['total_processes'] == 1000