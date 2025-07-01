"""Tests for Memory metrics collector."""

import pytest
from unittest.mock import patch, MagicMock
import asyncio

from ptop.collectors.memory import MemoryCollector
from ptop.collectors.base import BaseCollector


class TestMemoryCollector:
    """Test MemoryCollector class."""
    
    @pytest.fixture
    def memory_collector(self):
        """Create a MemoryCollector instance for testing."""
        return MemoryCollector()
    
    def test_inheritance(self, memory_collector):
        """Test that MemoryCollector inherits from BaseCollector."""
        assert isinstance(memory_collector, BaseCollector)
    
    def test_name_property(self, memory_collector):
        """Test collector name property."""
        assert memory_collector.name == "memory"
    
    def test_update_interval_property(self, memory_collector):
        """Test update interval property."""
        assert memory_collector.update_interval == 1.0
        assert isinstance(memory_collector.update_interval, float)
    
    @pytest.mark.asyncio
    async def test_collect_method_structure(self, memory_collector, mock_proc_meminfo):
        """Test that collect method returns expected structure."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 16777216000,  # 16GB in bytes
                    'MemFree': 8388608000,    # 8GB in bytes
                    'MemAvailable': 12582912000,  # 12GB in bytes
                    'Buffers': 524288000,     # 512MB in bytes
                    'Cached': 2097152000,     # 2GB in bytes
                    'SwapTotal': 4294967296,  # 4GB in bytes
                    'SwapFree': 4294967296,   # 4GB in bytes
                    'SwapCached': 0,
                    'Active': 4194304000,     # 4GB in bytes
                    'Inactive': 2097152000,   # 2GB in bytes
                    'Dirty': 33554432,       # 32MB in bytes
                    'Writeback': 0,
                    'Mapped': 536870912,     # 512MB in bytes
                    'Shmem': 268435456,      # 256MB in bytes
                    'Slab': 134217728,       # 128MB in bytes
                    'SReclaimable': 67108864, # 64MB in bytes
                    'SUnreclaim': 67108864    # 64MB in bytes
                }
                
                result = await memory_collector.collect()
                
                # Check that all main sections are present
                assert isinstance(result, dict)
                
                # Basic memory info
                assert 'mem_total' in result
                assert 'mem_free' in result
                assert 'mem_available' in result
                assert 'buffers' in result
                assert 'cached' in result
                
                # Calculated metrics
                assert 'mem_used' in result
                assert 'mem_used_percent' in result
                assert 'mem_available_percent' in result
                
                # Swap info
                assert 'swap_total' in result
                assert 'swap_free' in result
                assert 'swap_used' in result
                assert 'swap_used_percent' in result
    
    @pytest.mark.asyncio
    async def test_get_memory_info_success(self, memory_collector, mock_proc_meminfo):
        """Test successful memory info collection."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 16777216000,
                    'MemFree': 8388608000,
                    'MemAvailable': 12582912000,
                    'Buffers': 524288000,
                    'Cached': 2097152000,
                    'Slab': 134217728,
                    'SReclaimable': 67108864,
                    'SUnreclaim': 67108864,
                    'Active': 4194304000,
                    'Inactive': 2097152000,
                    'Active(anon)': 2097152000,
                    'Inactive(anon)': 1048576000,
                    'Active(file)': 2097152000,
                    'Inactive(file)': 1048576000,
                    'Dirty': 33554432,
                    'Writeback': 0,
                    'Mapped': 536870912,
                    'Shmem': 268435456
                }
                
                result = await memory_collector._get_memory_info()
                
                assert result['mem_total'] == 16777216000
                assert result['mem_free'] == 8388608000
                assert result['mem_available'] == 12582912000
                assert result['buffers'] == 524288000
                assert result['cached'] == 2097152000
                assert result['slab'] == 134217728
                assert result['sreclaimable'] == 67108864
                assert result['sunreclaim'] == 67108864
                assert result['active'] == 4194304000
                assert result['inactive'] == 2097152000
                assert result['active_anon'] == 2097152000
                assert result['inactive_anon'] == 1048576000
                assert result['active_file'] == 2097152000
                assert result['inactive_file'] == 1048576000
                assert result['dirty'] == 33554432
                assert result['writeback'] == 0
                assert result['mapped'] == 536870912
                assert result['shmem'] == 268435456
    
    @pytest.mark.asyncio
    async def test_get_memory_info_empty_file(self, memory_collector):
        """Test memory info with empty/missing file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await memory_collector._get_memory_info()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_memory_info_partial_data(self, memory_collector, mock_proc_meminfo):
        """Test memory info with partial data (missing some fields)."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                # Return only partial data
                mock_parse.return_value = {
                    'MemTotal': 16777216000,
                    'MemFree': 8388608000,
                    # Missing many fields
                }
                
                result = await memory_collector._get_memory_info()
                
                assert result['mem_total'] == 16777216000
                assert result['mem_free'] == 8388608000
                # Missing fields should default to 0
                assert result['mem_available'] == 0
                assert result['buffers'] == 0
                assert result['cached'] == 0
    
    @pytest.mark.asyncio
    async def test_get_swap_info_success(self, memory_collector, mock_proc_meminfo):
        """Test successful swap info collection."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'SwapTotal': 4294967296,
                    'SwapFree': 2147483648,
                    'SwapCached': 104857600
                }
                
                result = await memory_collector._get_swap_info()
                
                assert result['swap_total'] == 4294967296
                assert result['swap_free'] == 2147483648
                assert result['swap_cached'] == 104857600
    
    @pytest.mark.asyncio
    async def test_get_swap_info_empty_file(self, memory_collector):
        """Test swap info with empty/missing file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await memory_collector._get_swap_info()
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_swap_info_no_swap(self, memory_collector, mock_proc_meminfo):
        """Test swap info when swap is not configured."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'SwapTotal': 0,
                    'SwapFree': 0,
                    'SwapCached': 0
                }
                
                result = await memory_collector._get_swap_info()
                
                assert result['swap_total'] == 0
                assert result['swap_free'] == 0
                assert result['swap_cached'] == 0
    
    @pytest.mark.asyncio
    async def test_calculate_memory_metrics_with_available(self, memory_collector):
        """Test memory metrics calculation when MemAvailable is present."""
        metrics = {
            'mem_total': 16777216000,     # 16GB
            'mem_free': 8388608000,       # 8GB
            'mem_available': 12582912000, # 12GB
            'buffers': 524288000,         # 512MB
            'cached': 2097152000,         # 2GB
            'swap_total': 4294967296,     # 4GB
            'swap_free': 2147483648,      # 2GB
            'active': 4194304000,         # 4GB
            'inactive': 2097152000,       # 2GB
            'dirty': 33554432             # 32MB
        }
        
        result = await memory_collector._calculate_memory_metrics(metrics)
        
        # mem_used = mem_total - mem_available = 16GB - 12GB = 4GB
        assert result['mem_used'] == 4194304000
        assert result['mem_used_percent'] == 25.0  # (4GB/16GB)*100
        assert result['mem_available_percent'] == 75.0  # (12GB/16GB)*100
        assert result['buffers_percent'] == 3.125  # (512MB/16GB)*100
        assert result['cached_percent'] == 12.5  # (2GB/16GB)*100
        
        # swap_used = swap_total - swap_free = 4GB - 2GB = 2GB
        assert result['swap_used'] == 2147483648
        assert result['swap_used_percent'] == 50.0  # (2GB/4GB)*100
        
        # Active/Inactive percentages
        assert result['active_percent'] == 25.0  # (4GB/16GB)*100
        assert result['inactive_percent'] == 12.5  # (2GB/16GB)*100
        assert result['dirty_percent'] == 0.2  # (32MB/16GB)*100
    
    @pytest.mark.asyncio
    async def test_calculate_memory_metrics_without_available(self, memory_collector):
        """Test memory metrics calculation when MemAvailable is not present."""
        metrics = {
            'mem_total': 16777216000,  # 16GB
            'mem_free': 8388608000,    # 8GB
            'mem_available': 0,        # Not available
            'buffers': 524288000,      # 512MB
            'cached': 2097152000,      # 2GB
            'swap_total': 0,           # No swap
            'swap_free': 0,
            'active': 4194304000,      # 4GB
            'inactive': 2097152000,    # 2GB
            'dirty': 33554432          # 32MB
        }
        
        result = await memory_collector._calculate_memory_metrics(metrics)
        
        # Fallback calculation: mem_used = mem_total - mem_free - buffers - cached
        # = 16GB - 8GB - 512MB - 2GB = 5.5GB
        expected_used = 16777216000 - 8388608000 - 524288000 - 2097152000
        assert result['mem_used'] == expected_used
        assert result['mem_available_percent'] == 0  # MemAvailable not present
        
        # No swap
        assert result['swap_used'] == 0
        assert result['swap_used_percent'] == 0
    
    @pytest.mark.asyncio
    async def test_calculate_memory_metrics_zero_total(self, memory_collector):
        """Test memory metrics calculation with zero total memory."""
        metrics = {
            'mem_total': 0,
            'mem_free': 0,
            'mem_available': 0,
            'buffers': 0,
            'cached': 0,
            'swap_total': 0,
            'swap_free': 0,
            'active': 0,
            'inactive': 0,
            'dirty': 0
        }
        
        result = await memory_collector._calculate_memory_metrics(metrics)
        
        # Should handle zero division gracefully
        assert result['mem_used'] == 0
        assert result['swap_used'] == 0
        assert result['swap_used_percent'] == 0
        # Percentages should not be calculated when total is 0
        assert 'mem_used_percent' not in result or result.get('mem_used_percent') == 0
    
    @pytest.mark.asyncio
    async def test_calculate_memory_metrics_negative_values(self, memory_collector):
        """Test memory metrics calculation handles negative values."""
        metrics = {
            'mem_total': 1000,
            'mem_free': 1200,  # Free > Total (edge case)
            'mem_available': 800,
            'buffers': 100,
            'cached': 200,
            'swap_total': 1000,
            'swap_free': 1200,  # Free > Total (edge case)
            'active': 500,
            'inactive': 300,
            'dirty': 50
        }
        
        result = await memory_collector._calculate_memory_metrics(metrics)
        
        # Should handle edge cases and ensure non-negative values
        assert result['mem_used'] >= 0
        assert result['swap_used'] >= 0
    
    @pytest.mark.asyncio
    async def test_full_collect_integration(self, memory_collector, mock_proc_meminfo):
        """Test full collect method integration."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 16777216000,
                    'MemFree': 8388608000,
                    'MemAvailable': 12582912000,
                    'Buffers': 524288000,
                    'Cached': 2097152000,
                    'SwapTotal': 4294967296,
                    'SwapFree': 2147483648,
                    'SwapCached': 0,
                    'Active': 4194304000,
                    'Inactive': 2097152000,
                    'Dirty': 33554432,
                    'Writeback': 0,
                    'Mapped': 536870912,
                    'Shmem': 268435456,
                    'Slab': 134217728,
                    'SReclaimable': 67108864,
                    'SUnreclaim': 67108864
                }
                
                result = await memory_collector.collect()
                
                # Verify all expected keys are present
                expected_keys = [
                    'mem_total', 'mem_free', 'mem_available', 'buffers', 'cached',
                    'swap_total', 'swap_free', 'swap_cached',
                    'mem_used', 'mem_used_percent', 'mem_available_percent',
                    'buffers_percent', 'cached_percent',
                    'swap_used', 'swap_used_percent',
                    'active', 'inactive', 'dirty', 'writeback', 'mapped', 'shmem',
                    'slab', 'sreclaimable', 'sunreclaim',
                    'active_percent', 'inactive_percent', 'dirty_percent'
                ]
                
                for key in expected_keys:
                    assert key in result, f"Key '{key}' missing from result"
                
                # Verify calculated values are reasonable
                assert result['mem_total'] > 0
                assert 0 <= result['mem_used_percent'] <= 100
                assert 0 <= result['swap_used_percent'] <= 100
    
    @pytest.mark.asyncio
    async def test_collect_with_failures(self, memory_collector):
        """Test collect method when meminfo fails to read."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await memory_collector.collect()
            
            # Should return dict with default values
            assert isinstance(result, dict)
            # Most values should be 0 or missing when no data is available
            expected_zero_keys = ['swap_used', 'swap_used_percent']
            for key in expected_zero_keys:
                assert result.get(key) == 0
    
    @pytest.mark.asyncio
    async def test_collect_multiple_calls_consistency(self, memory_collector, mock_proc_meminfo):
        """Test that multiple collect calls return consistent data.""" 
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_meminfo):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 16777216000,
                    'MemFree': 8388608000,
                    'MemAvailable': 12582912000,
                    'Buffers': 524288000,
                    'Cached': 2097152000,
                    'SwapTotal': 4294967296,
                    'SwapFree': 2147483648
                }
                
                result1 = await memory_collector.collect()
                result2 = await memory_collector.collect()
                
                # Results should be identical for same input
                assert result1['mem_total'] == result2['mem_total']
                assert result1['mem_used_percent'] == result2['mem_used_percent']
                assert result1['swap_used_percent'] == result2['swap_used_percent']
    
    def test_memory_collector_thread_safety(self, memory_collector):
        """Test that multiple instances don't interfere with each other."""
        collector2 = MemoryCollector()
        
        # Each instance should be independent
        assert memory_collector.name == collector2.name
        assert memory_collector.update_interval == collector2.update_interval
        
        # They should be separate objects
        assert memory_collector is not collector2
    
    @pytest.mark.asyncio
    async def test_edge_case_very_large_memory(self, memory_collector):
        """Test handling of very large memory values."""
        with patch('ptop.utils.helpers.read_proc_file', return_value="mock"):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                # Very large memory values (e.g., 1TB system)
                mock_parse.return_value = {
                    'MemTotal': 1099511627776,  # 1TB
                    'MemFree': 549755813888,    # 512GB
                    'MemAvailable': 824633720832, # 768GB
                    'SwapTotal': 107374182400,  # 100GB
                    'SwapFree': 53687091200     # 50GB
                }
                
                result = await memory_collector.collect()
                
                # Should handle large numbers correctly
                assert result['mem_total'] == 1099511627776
                assert result['mem_used'] > 0
                assert 0 <= result['mem_used_percent'] <= 100
                assert 0 <= result['swap_used_percent'] <= 100
    
    @pytest.mark.asyncio
    async def test_edge_case_all_memory_used(self, memory_collector):
        """Test edge case where all memory is used."""
        with patch('ptop.utils.helpers.read_proc_file', return_value="mock"):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 1073741824,  # 1GB
                    'MemFree': 0,            # No free memory
                    'MemAvailable': 0,       # No available memory
                    'Buffers': 0,
                    'Cached': 0,
                    'SwapTotal': 1073741824, # 1GB
                    'SwapFree': 0            # No free swap
                }
                
                result = await memory_collector.collect()
                
                assert result['mem_used_percent'] == 100.0
                assert result['swap_used_percent'] == 100.0
    
    @pytest.mark.asyncio
    async def test_edge_case_no_swap_configured(self, memory_collector):
        """Test system with no swap configured."""
        with patch('ptop.utils.helpers.read_proc_file', return_value="mock"):
            with patch('ptop.utils.helpers.parse_meminfo') as mock_parse:
                mock_parse.return_value = {
                    'MemTotal': 1073741824,  # 1GB
                    'MemFree': 536870912,    # 512MB
                    'MemAvailable': 805306368, # 768MB
                    'SwapTotal': 0,          # No swap
                    'SwapFree': 0,
                    'SwapCached': 0
                }
                
                result = await memory_collector.collect()
                
                assert result['swap_total'] == 0
                assert result['swap_used'] == 0
                assert result['swap_used_percent'] == 0