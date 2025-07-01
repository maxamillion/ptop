"""Tests for CPU metrics collector."""

import pytest
from unittest.mock import patch, MagicMock
import asyncio

from ptop.collectors.cpu import CPUCollector
from ptop.collectors.base import BaseCollector


class TestCPUCollector:
    """Test CPUCollector class."""
    
    @pytest.fixture
    def cpu_collector(self):
        """Create a CPUCollector instance for testing."""
        return CPUCollector()
    
    def test_inheritance(self, cpu_collector):
        """Test that CPUCollector inherits from BaseCollector."""
        assert isinstance(cpu_collector, BaseCollector)
    
    def test_name_property(self, cpu_collector):
        """Test collector name property."""
        assert cpu_collector.name == "cpu"
    
    def test_update_interval_property(self, cpu_collector):
        """Test update interval property."""
        assert cpu_collector.update_interval == 1.0
        assert isinstance(cpu_collector.update_interval, float)
    
    def test_initialization(self, cpu_collector):
        """Test collector initialization."""
        assert cpu_collector._previous_cpu_times == {}
        assert cpu_collector._cpu_count is None
    
    @pytest.mark.asyncio
    async def test_collect_method_structure(self, cpu_collector, mock_proc_stat, mock_proc_cpuinfo, mock_proc_loadavg):
        """Test that collect method returns expected structure."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            # Mock different files based on path
            def mock_read_side_effect(path):
                if path == '/proc/cpuinfo':
                    return mock_proc_cpuinfo
                elif path == '/proc/stat':
                    return mock_proc_stat
                elif path == '/proc/loadavg':
                    return mock_proc_loadavg
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            result = await cpu_collector.collect()
            
            # Check that all main sections are present
            assert isinstance(result, dict)
            assert 'cpu_count' in result
            assert 'model_name' in result
            assert 'cpu_percentages' in result
            assert 'load_1min' in result
            assert 'load_5min' in result
            assert 'load_15min' in result
    
    @pytest.mark.asyncio
    async def test_get_cpu_info(self, cpu_collector, mock_proc_cpuinfo):
        """Test _get_cpu_info method."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_cpuinfo):
            result = await cpu_collector._get_cpu_info()
            
            assert result['cpu_count'] == 2  # Based on mock data
            assert result['model_name'] == 'Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz'
            assert cpu_collector._cpu_count == 2
    
    @pytest.mark.asyncio
    async def test_get_cpu_info_empty_file(self, cpu_collector):
        """Test _get_cpu_info with empty/missing file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await cpu_collector._get_cpu_info()
            assert result == {}
            assert cpu_collector._cpu_count is None
    
    @pytest.mark.asyncio
    async def test_get_cpu_info_malformed_data(self, cpu_collector):
        """Test _get_cpu_info with malformed data."""
        malformed_data = "invalid\ndata\nhere"
        with patch('ptop.utils.helpers.read_proc_file', return_value=malformed_data):
            result = await cpu_collector._get_cpu_info()
            assert 'cpu_count' in result
            assert 'model_name' in result
            assert result['model_name'] == 'Unknown'
    
    @pytest.mark.asyncio
    async def test_get_cpu_usage_first_run(self, cpu_collector, mock_proc_stat):
        """Test CPU usage calculation on first run (no previous data)."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_stat):
            with patch('ptop.utils.helpers.parse_proc_stat_line') as mock_parse:
                mock_parse.return_value = {
                    'user': 123456, 'nice': 0, 'system': 234567, 'idle': 890123,
                    'iowait': 4567, 'irq': 0, 'softirq': 1234
                }
                
                result = await cpu_collector._get_cpu_usage()
                
                # First run should return 0% for all CPUs
                assert 'cpu_percentages' in result
                assert result['cpu_percentages']['cpu'] == 0.0
                assert result['overall_cpu_usage'] == 0.0
                assert 'per_core_usage' in result
    
    @pytest.mark.asyncio
    async def test_get_cpu_usage_with_previous_data(self, cpu_collector, mock_proc_stat):
        """Test CPU usage calculation with previous data."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_stat):
            with patch('ptop.utils.helpers.parse_proc_stat_line') as mock_parse:
                with patch('ptop.utils.helpers.calculate_cpu_percentage', return_value=25.5):
                    # Set up previous data
                    cpu_collector._previous_cpu_times = {
                        'cpu': {'user': 100000, 'system': 200000, 'idle': 800000}
                    }
                    
                    mock_parse.return_value = {
                        'user': 123456, 'nice': 0, 'system': 234567, 'idle': 890123,
                        'iowait': 4567, 'irq': 0, 'softirq': 1234
                    }
                    
                    result = await cpu_collector._get_cpu_usage()
                    
                    assert result['cpu_percentages']['cpu'] == 25.5
                    assert result['overall_cpu_usage'] == 25.5
    
    @pytest.mark.asyncio
    async def test_get_cpu_usage_empty_file(self, cpu_collector):
        """Test CPU usage with empty/missing stat file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await cpu_collector._get_cpu_usage()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_cpu_usage_per_core(self, cpu_collector, mock_proc_stat):
        """Test per-core CPU usage calculation."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_stat):
            with patch('ptop.utils.helpers.parse_proc_stat_line') as mock_parse:
                with patch('ptop.utils.helpers.calculate_cpu_percentage', return_value=30.0):
                    # Mock parse_proc_stat_line to return data for multiple CPUs
                    def parse_side_effect(line):
                        if line.startswith('cpu '):
                            return {'user': 123456, 'system': 234567, 'idle': 890123}
                        elif line.startswith('cpu0'):
                            return {'user': 61728, 'system': 117283, 'idle': 445061}
                        elif line.startswith('cpu1'):
                            return {'user': 61728, 'system': 117284, 'idle': 445062}
                        return {}
                    
                    mock_parse.side_effect = parse_side_effect
                    
                    # Set up previous data for all CPUs
                    cpu_collector._previous_cpu_times = {
                        'cpu': {'user': 100000, 'system': 200000, 'idle': 800000},
                        'cpu0': {'user': 50000, 'system': 100000, 'idle': 400000},
                        'cpu1': {'user': 50000, 'system': 100000, 'idle': 400000}
                    }
                    
                    result = await cpu_collector._get_cpu_usage()
                    
                    assert 'per_core_usage' in result
                    assert 'core_0' in result['per_core_usage']
                    assert 'core_1' in result['per_core_usage']
                    assert result['per_core_usage']['core_0'] == 30.0
                    assert result['per_core_usage']['core_1'] == 30.0
    
    @pytest.mark.asyncio
    async def test_get_load_averages(self, cpu_collector, mock_proc_loadavg):
        """Test load average calculation."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_loadavg):
            cpu_collector._cpu_count = 2  # Set CPU count for percentage calculation
            
            result = await cpu_collector._get_load_averages()
            
            assert result['load_1min'] == 1.23
            assert result['load_5min'] == 2.34
            assert result['load_15min'] == 3.45
            assert result['load_1min_percent'] == 61.5  # (1.23/2)*100
            assert result['load_5min_percent'] == 117.0  # (2.34/2)*100
            assert result['load_15min_percent'] == 172.5  # (3.45/2)*100
    
    @pytest.mark.asyncio
    async def test_get_load_averages_without_cpu_count(self, cpu_collector, mock_proc_loadavg):
        """Test load averages without CPU count (no percentages)."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_loadavg):
            cpu_collector._cpu_count = None
            
            result = await cpu_collector._get_load_averages()
            
            assert result['load_1min'] == 1.23
            assert result['load_5min'] == 2.34  
            assert result['load_15min'] == 3.45
            assert 'load_1min_percent' not in result
            assert 'load_5min_percent' not in result
            assert 'load_15min_percent' not in result
    
    @pytest.mark.asyncio
    async def test_get_load_averages_empty_file(self, cpu_collector):
        """Test load averages with empty/missing file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await cpu_collector._get_load_averages()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_load_averages_malformed_data(self, cpu_collector):
        """Test load averages with malformed data."""
        with patch('ptop.utils.helpers.read_proc_file', return_value="invalid"):
            result = await cpu_collector._get_load_averages()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_cpu_frequencies(self, cpu_collector, mock_proc_cpuinfo):
        """Test CPU frequency collection."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_cpuinfo):
            result = await cpu_collector._get_cpu_frequencies()
            
            assert 'cpu_frequencies_mhz' in result
            assert 'avg_frequency_mhz' in result
            assert result['cpu_frequencies_mhz'] == [2400.0, 2401.0]
            assert result['avg_frequency_mhz'] == 2400.5
    
    @pytest.mark.asyncio
    async def test_get_cpu_frequencies_no_data(self, cpu_collector):
        """Test CPU frequencies with no data."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await cpu_collector._get_cpu_frequencies()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_cpu_frequencies_malformed_data(self, cpu_collector):
        """Test CPU frequencies with malformed frequency data."""
        malformed_cpuinfo = """processor	: 0
vendor_id	: GenuineIntel
cpu MHz		: invalid_freq
cache size	: 8192 KB"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=malformed_cpuinfo):
            result = await cpu_collector._get_cpu_frequencies()
            # Should handle ValueError gracefully
            assert 'cpu_frequencies_mhz' not in result or result['cpu_frequencies_mhz'] == []
    
    @pytest.mark.asyncio
    async def test_get_cpu_frequencies_exception_handling(self, cpu_collector):
        """Test CPU frequencies exception handling."""
        with patch('ptop.utils.helpers.read_proc_file', side_effect=Exception("Test error")):
            result = await cpu_collector._get_cpu_frequencies()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_full_collect_integration(self, cpu_collector, mock_proc_stat, 
                                          mock_proc_cpuinfo, mock_proc_loadavg):
        """Test full collect method integration."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/cpuinfo':
                    return mock_proc_cpuinfo
                elif path == '/proc/stat':
                    return mock_proc_stat
                elif path == '/proc/loadavg':
                    return mock_proc_loadavg
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('ptop.utils.helpers.parse_proc_stat_line') as mock_parse:
                mock_parse.return_value = {
                    'user': 123456, 'nice': 0, 'system': 234567, 'idle': 890123,
                    'iowait': 4567, 'irq': 0, 'softirq': 1234
                }
                
                result = await cpu_collector.collect()
                
                # Verify all expected keys are present
                expected_keys = [
                    'cpu_count', 'model_name', 'cpu_percentages', 'overall_cpu_usage',
                    'per_core_usage', 'load_1min', 'load_5min', 'load_15min',
                    'load_1min_percent', 'load_5min_percent', 'load_15min_percent',
                    'cpu_frequencies_mhz', 'avg_frequency_mhz'
                ]
                
                for key in expected_keys:
                    assert key in result
    
    @pytest.mark.asyncio
    async def test_collect_with_all_failures(self, cpu_collector):
        """Test collect method when all proc files fail to read."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await cpu_collector.collect()
            
            # Should return empty dict for each section
            assert isinstance(result, dict)
    
    def test_cpu_collector_state_persistence(self, cpu_collector):
        """Test that collector maintains state between calls."""
        # Initially empty
        assert cpu_collector._previous_cpu_times == {}
        assert cpu_collector._cpu_count is None
        
        # Set some state
        cpu_collector._previous_cpu_times = {'cpu': {'user': 100, 'system': 200}}
        cpu_collector._cpu_count = 4
        
        # State should persist
        assert cpu_collector._previous_cpu_times == {'cpu': {'user': 100, 'system': 200}}
        assert cpu_collector._cpu_count == 4
    
    @pytest.mark.asyncio
    async def test_collect_multiple_calls_state_management(self, cpu_collector, mock_proc_stat, 
                                                         mock_proc_cpuinfo, mock_proc_loadavg):
        """Test that multiple collect calls properly manage state."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/cpuinfo':
                    return mock_proc_cpuinfo
                elif path == '/proc/stat':
                    return mock_proc_stat
                elif path == '/proc/loadavg':
                    return mock_proc_loadavg
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('ptop.utils.helpers.parse_proc_stat_line') as mock_parse:
                mock_parse.return_value = {
                    'user': 123456, 'nice': 0, 'system': 234567, 'idle': 890123,
                    'iowait': 4567, 'irq': 0, 'softirq': 1234
                }
                
                # First call
                result1 = await cpu_collector.collect()
                assert cpu_collector._cpu_count == 2  # Should be set from cpuinfo
                assert len(cpu_collector._previous_cpu_times) > 0  # Should have CPU times stored
                
                # Second call
                result2 = await cpu_collector.collect()
                assert cpu_collector._cpu_count == 2  # Should persist
                # Previous times should be updated for second call
                assert len(cpu_collector._previous_cpu_times) > 0
    
    def test_cpu_collector_thread_safety(self, cpu_collector):
        """Test basic thread safety considerations."""
        # The collector should not share mutable state between instances
        collector2 = CPUCollector()
        
        cpu_collector._previous_cpu_times = {'cpu': {'user': 100}}
        collector2._previous_cpu_times = {'cpu': {'user': 200}}
        
        # Each instance should have its own state
        assert cpu_collector._previous_cpu_times != collector2._previous_cpu_times
        assert cpu_collector._previous_cpu_times['cpu']['user'] == 100
        assert collector2._previous_cpu_times['cpu']['user'] == 200