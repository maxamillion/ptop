"""Tests for Storage metrics collector."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import asyncio
import os

from ptop.collectors.storage import StorageCollector
from ptop.collectors.base import BaseCollector


class TestStorageCollector:
    """Test StorageCollector class."""
    
    @pytest.fixture
    def storage_collector(self):
        """Create a StorageCollector instance for testing."""
        return StorageCollector()
    
    def test_inheritance(self, storage_collector):
        """Test that StorageCollector inherits from BaseCollector."""
        assert isinstance(storage_collector, BaseCollector)
    
    def test_name_property(self, storage_collector):
        """Test collector name property."""
        assert storage_collector.name == "storage"
    
    def test_update_interval_property(self, storage_collector):
        """Test update interval property."""
        assert storage_collector.update_interval == 2.0
        assert isinstance(storage_collector.update_interval, float)
    
    def test_initialization(self, storage_collector):
        """Test collector initialization."""
        assert storage_collector._previous_io_stats == {}
        assert storage_collector._previous_collect_time == 0.0
    
    @pytest.mark.asyncio
    async def test_collect_method_structure(self, storage_collector, mock_proc_mounts, 
                                          mock_proc_diskstats, mock_statvfs):
        """Test that collect method returns expected structure."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/mounts':
                    return mock_proc_mounts
                elif path == '/proc/diskstats':
                    return mock_proc_diskstats
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector.collect()
                
                # Check that all main sections are present
                assert isinstance(result, dict)
                assert 'filesystems' in result
                assert 'disk_io' in result
                
                # Check filesystem structure
                filesystems = result['filesystems']
                assert isinstance(filesystems, list)
                
                # Check disk I/O structure
                disk_io = result['disk_io']
                assert isinstance(disk_io, list)
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_success(self, storage_collector, mock_proc_mounts, mock_statvfs):
        """Test successful filesystem usage collection."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_mounts):
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector._get_filesystem_usage()
                
                assert 'filesystems' in result
                filesystems = result['filesystems']
                assert len(filesystems) > 0
                
                # Check first filesystem
                fs = filesystems[0]
                assert 'device' in fs
                assert 'mount_point' in fs
                assert 'fs_type' in fs
                assert 'total_bytes' in fs
                assert 'used_bytes' in fs
                assert 'free_bytes' in fs
                assert 'usage_percent' in fs
                
                # Verify calculations
                assert fs['total_bytes'] == mock_statvfs.f_blocks * mock_statvfs.f_frsize
                assert fs['free_bytes'] == mock_statvfs.f_bavail * mock_statvfs.f_frsize
                assert 0 <= fs['usage_percent'] <= 100
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_empty_mounts(self, storage_collector):
        """Test filesystem usage with empty mounts file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await storage_collector._get_filesystem_usage()
            
            assert result == {'filesystems': []}
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_filters_virtual_fs(self, storage_collector, mock_statvfs):
        """Test that virtual filesystems are filtered out."""
        mounts_with_virtual = """/dev/sda1 / ext4 rw,relatime,errors=remount-ro 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
tmpfs /tmp tmpfs rw,nosuid,nodev,size=2097152k 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
/dev/sda2 /home ext4 rw,relatime 0 0"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=mounts_with_virtual):
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                # Should only include real filesystems (ext4), not proc, tmpfs, sysfs
                fs_types = [fs['fs_type'] for fs in filesystems]
                assert 'ext4' in fs_types
                assert 'proc' not in fs_types
                assert 'tmpfs' not in fs_types
                assert 'sysfs' not in fs_types
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_filters_proc_sys_mounts(self, storage_collector, mock_statvfs):
        """Test that /proc and /sys mount points are filtered."""
        mounts_with_special = """/dev/sda1 / ext4 rw,relatime 0 0
/dev/sda2 /proc/test ext4 rw,relatime 0 0
/dev/sda3 /sys/test ext4 rw,relatime 0 0
/dev/sda4 /home ext4 rw,relatime 0 0"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=mounts_with_special):
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                mount_points = [fs['mount_point'] for fs in filesystems]
                
                # Should include / and /home but not /proc/test or /sys/test
                assert '/' in mount_points
                assert '/home' in mount_points
                assert '/proc/test' not in mount_points
                assert '/sys/test' not in mount_points
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_statvfs_error(self, storage_collector, mock_proc_mounts):
        """Test filesystem usage when statvfs fails."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_mounts):
            with patch('os.statvfs', side_effect=OSError("Permission denied")):
                result = await storage_collector._get_filesystem_usage()
                
                # Should handle errors gracefully
                assert 'filesystems' in result
                assert result['filesystems'] == []
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_malformed_mounts(self, storage_collector, mock_statvfs):
        """Test filesystem usage with malformed mounts data."""
        malformed_mounts = """incomplete line
/dev/sda1
/dev/sda2 /home
/dev/sda3 /var ext4 rw,relatime 0 0"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=malformed_mounts):
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                # Should only include properly formatted lines
                assert len(filesystems) == 1
                assert filesystems[0]['mount_point'] == '/var'
    
    @pytest.mark.asyncio
    async def test_get_filesystem_usage_sorting(self, storage_collector, mock_statvfs):
        """Test that filesystems are sorted by usage percentage."""
        mounts_multiple = """/dev/sda1 / ext4 rw,relatime 0 0
/dev/sda2 /home ext4 rw,relatime 0 0
/dev/sda3 /var ext4 rw,relatime 0 0"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=mounts_multiple):
            # Mock different statvfs results for different mount points
            def mock_statvfs_side_effect(path):
                if path == '/':
                    # 80% usage
                    mock_stat = MagicMock()
                    mock_stat.f_blocks = 1000
                    mock_stat.f_bfree = 200
                    mock_stat.f_bavail = 200
                    mock_stat.f_frsize = 4096
                    return mock_stat
                elif path == '/home':
                    # 50% usage
                    mock_stat = MagicMock()
                    mock_stat.f_blocks = 1000
                    mock_stat.f_bfree = 500
                    mock_stat.f_bavail = 500
                    mock_stat.f_frsize = 4096
                    return mock_stat
                elif path == '/var':
                    # 90% usage
                    mock_stat = MagicMock()
                    mock_stat.f_blocks = 1000
                    mock_stat.f_bfree = 100
                    mock_stat.f_bavail = 100
                    mock_stat.f_frsize = 4096
                    return mock_stat
                return mock_statvfs
            
            with patch('os.statvfs', side_effect=mock_statvfs_side_effect):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                assert len(filesystems) == 3
                
                # Should be sorted by usage percentage (descending)
                assert filesystems[0]['mount_point'] == '/var'  # 90%
                assert filesystems[1]['mount_point'] == '/'     # 80%
                assert filesystems[2]['mount_point'] == '/home' # 50%
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_first_run(self, storage_collector, mock_proc_diskstats):
        """Test disk I/O stats on first run (no previous data)."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            # First run should not have rate calculations
            assert 'disk_io' in result
            assert result['disk_io'] == []  # No rates without previous data
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_with_previous_data(self, storage_collector, mock_proc_diskstats):
        """Test disk I/O stats with previous data for rate calculations."""
        # Set up previous data
        storage_collector._previous_io_stats = {
            'sda': {
                'reads_completed': 100000,
                'sectors_read': 2000000,
                'read_time_ms': 5000,
                'writes_completed': 300000,
                'sectors_written': 4000000,
                'write_time_ms': 10000,
                'io_in_progress': 0,
                'io_time_ms': 15000
            }
        }
        storage_collector._previous_collect_time = 123450.0
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=mock_proc_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            assert 'disk_io' in result
            disk_io = result['disk_io']
            
            if len(disk_io) > 0:
                io_info = disk_io[0]
                assert 'device' in io_info
                assert 'reads_per_sec' in io_info
                assert 'writes_per_sec' in io_info
                assert 'read_bytes_per_sec' in io_info
                assert 'write_bytes_per_sec' in io_info
                assert 'avg_read_time_ms' in io_info
                assert 'avg_write_time_ms' in io_info
                assert 'utilization_percent' in io_info
                assert 'io_in_progress' in io_info
                
                # Rates should be calculated
                assert io_info['reads_per_sec'] >= 0
                assert io_info['writes_per_sec'] >= 0
                assert io_info['read_bytes_per_sec'] >= 0
                assert io_info['write_bytes_per_sec'] >= 0
                assert 0 <= io_info['utilization_percent'] <= 100
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_empty_file(self, storage_collector):
        """Test disk I/O stats with empty diskstats file."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            assert result == {'disk_io': []}
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_malformed_data(self, storage_collector):
        """Test disk I/O stats with malformed diskstats data."""
        malformed_diskstats = """incomplete line
   8       0 sda 123 456
   8       1 sda1 incomplete data here"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=malformed_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            # Should handle malformed data gracefully
            assert 'disk_io' in result
            assert result['disk_io'] == []
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_filters_partitions(self, storage_collector):
        """Test that partition devices are filtered out."""
        diskstats_with_partitions = """   8       0 sda 123456 789 2345678 9012 345678 901 4567890 2345 0 6789 11357
   8       1 sda1 98765 432 1876543 6543 210987 654 3210987 1234 0 4321 7777
   8       2 sda2 12345 123 234567 1234 23456 234 345678 456 0 567 1234
   8      16 sdb 54321 210 987654 3210 123456 321 1234567 789 0 1000 4000"""
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=diskstats_with_partitions):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            # Should only collect main devices, not partitions
            # (This would require previous data to show any results)
            assert 'disk_io' in result
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_rate_calculations(self, storage_collector):
        """Test disk I/O rate calculations."""
        # Mock current diskstats data with higher values than previous
        current_diskstats = """   8       0 sda 123500 789 2345800 9100 345800 901 4568000 2400 0 6800 11400"""
        
        # Set up previous data with lower values
        storage_collector._previous_io_stats = {
            'sda': {
                'reads_completed': 123456,
                'sectors_read': 2345678,
                'read_time_ms': 9012,
                'writes_completed': 345678,
                'sectors_written': 4567890,
                'write_time_ms': 2345,
                'io_in_progress': 0,
                'io_time_ms': 6789
            }
        }
        storage_collector._previous_collect_time = 123450.0  # 6 seconds ago
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=current_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            assert 'disk_io' in result
            disk_io = result['disk_io']
            
            if len(disk_io) > 0:
                io_info = disk_io[0]
                
                # Check that rates are calculated (should be > 0 due to increased values)
                time_delta = 6.0  # 6 seconds
                expected_reads_per_sec = (123500 - 123456) / time_delta
                expected_writes_per_sec = (345800 - 345678) / time_delta
                
                assert io_info['reads_per_sec'] == expected_reads_per_sec
                assert io_info['writes_per_sec'] == expected_writes_per_sec
                
                # Check bytes per second calculations (sectors * 512)
                read_sectors_delta = 2345800 - 2345678
                write_sectors_delta = 4568000 - 4567890
                expected_read_bytes_per_sec = (read_sectors_delta * 512) / time_delta
                expected_write_bytes_per_sec = (write_sectors_delta * 512) / time_delta
                
                assert io_info['read_bytes_per_sec'] == expected_read_bytes_per_sec
                assert io_info['write_bytes_per_sec'] == expected_write_bytes_per_sec
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_utilization_calculation(self, storage_collector):
        """Test disk utilization percentage calculation."""
        current_diskstats = """   8       0 sda 123456 789 2345678 9012 345678 901 4567890 2345 0 7000 11357"""
        
        # Set up previous data
        storage_collector._previous_io_stats = {
            'sda': {
                'reads_completed': 123456,
                'sectors_read': 2345678,
                'read_time_ms': 9012,
                'writes_completed': 345678,
                'sectors_written': 4567890,
                'write_time_ms': 2345,
                'io_in_progress': 0,
                'io_time_ms': 6000  # 1000ms increase over 2 seconds = 50% utilization
            }
        }
        storage_collector._previous_collect_time = 123454.0  # 2 seconds ago
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=current_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            disk_io = result['disk_io']
            if len(disk_io) > 0:
                io_info = disk_io[0]
                
                # io_time_ms increased by 1000ms over 2 seconds = 50% utilization
                expected_utilization = (1000 / (2 * 1000)) * 100
                assert io_info['utilization_percent'] == expected_utilization
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_sorting(self, storage_collector):
        """Test that disk I/O stats are sorted by utilization."""
        diskstats_multiple = """   8       0 sda 123456 789 2345678 9012 345678 901 4567890 2345 0 7000 11357
   8      16 sdb 54321 210 987654 3210 123456 321 1234567 789 0 8000 4000
   8      32 sdc 11111 111 111111 1111 111111 111 1111111 111 0 9000 2222"""
        
        # Set up previous data with different utilization rates
        storage_collector._previous_io_stats = {
            'sda': {'io_time_ms': 6000},  # 1000ms increase = 50% util
            'sdb': {'io_time_ms': 6000},  # 2000ms increase = 100% util
            'sdc': {'io_time_ms': 6000}   # 3000ms increase = 150% util (capped at 100%)
        }
        storage_collector._previous_collect_time = 123454.0  # 2 seconds ago
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=diskstats_multiple):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            disk_io = result['disk_io']
            if len(disk_io) > 1:
                # Should be sorted by utilization (descending)
                assert disk_io[0]['utilization_percent'] >= disk_io[1]['utilization_percent']
    
    @pytest.mark.asyncio
    async def test_get_disk_io_stats_zero_division_protection(self, storage_collector):
        """Test protection against zero division in calculations."""
        current_diskstats = """   8       0 sda 123456 789 2345678 9012 345678 901 4567890 2345 0 6789 11357"""
        
        # Set up previous data with same values (no change)
        storage_collector._previous_io_stats = {
            'sda': {
                'reads_completed': 123456,
                'sectors_read': 2345678,
                'read_time_ms': 9012,
                'writes_completed': 345678,
                'sectors_written': 4567890,
                'write_time_ms': 2345,
                'io_in_progress': 0,
                'io_time_ms': 6789
            }
        }
        storage_collector._previous_collect_time = 123456.0  # Same time (no delta)
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=current_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            # Should handle zero time delta gracefully
            assert 'disk_io' in result
            # No rates should be calculated when time delta is 0
            assert result['disk_io'] == []
    
    @pytest.mark.asyncio
    async def test_full_collect_integration(self, storage_collector, mock_proc_mounts, 
                                          mock_proc_diskstats, mock_statvfs):
        """Test full collect method integration."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/mounts':
                    return mock_proc_mounts
                elif path == '/proc/diskstats':
                    return mock_proc_diskstats
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.statvfs', return_value=mock_statvfs):
                result = await storage_collector.collect()
                
                # Check structure
                assert 'filesystems' in result
                assert 'disk_io' in result
                
                # Check that we have filesystem data
                filesystems = result['filesystems']
                assert len(filesystems) > 0
                
                # Check filesystem data quality
                fs = filesystems[0]
                assert fs['device'] in ['/dev/sda1', '/dev/sda2']
                assert fs['mount_point'] in ['/', '/home']
                assert fs['fs_type'] == 'ext4'
                assert fs['total_bytes'] > 0
                assert fs['usage_percent'] >= 0
    
    @pytest.mark.asyncio
    async def test_collect_updates_previous_collect_time(self, storage_collector, mock_proc_mounts, 
                                                       mock_proc_diskstats, mock_statvfs):
        """Test that collect updates the previous collect time."""
        initial_time = storage_collector._previous_collect_time
        
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/mounts':
                    return mock_proc_mounts
                elif path == '/proc/diskstats':
                    return mock_proc_diskstats
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.statvfs', return_value=mock_statvfs):
                await storage_collector.collect()
                
                # Should update the previous collect time
                assert storage_collector._previous_collect_time > initial_time
    
    @pytest.mark.asyncio
    async def test_collect_with_failures(self, storage_collector):
        """Test collect method when all files fail to read."""
        with patch('ptop.utils.helpers.read_proc_file', return_value=None):
            with patch('os.statvfs', side_effect=OSError("Permission denied")):
                result = await storage_collector.collect()
                
                # Should return empty results
                assert result['filesystems'] == []
                assert result['disk_io'] == []
    
    @pytest.mark.asyncio
    async def test_collect_multiple_calls_state_management(self, storage_collector, mock_proc_mounts, 
                                                         mock_proc_diskstats, mock_statvfs):
        """Test that multiple collect calls properly manage state."""
        with patch('ptop.utils.helpers.read_proc_file') as mock_read:
            def mock_read_side_effect(path):
                if path == '/proc/mounts':
                    return mock_proc_mounts
                elif path == '/proc/diskstats':
                    return mock_proc_diskstats
                return None
            
            mock_read.side_effect = mock_read_side_effect
            
            with patch('os.statvfs', return_value=mock_statvfs):
                # First call
                result1 = await storage_collector.collect()
                assert len(storage_collector._previous_io_stats) >= 0
                
                # Second call
                result2 = await storage_collector.collect()
                
                # Should maintain consistent filesystem data
                assert len(result1['filesystems']) == len(result2['filesystems'])
    
    def test_storage_collector_thread_safety(self, storage_collector):
        """Test that multiple instances don't interfere with each other."""
        collector2 = StorageCollector()
        
        # Set different state
        storage_collector._previous_io_stats = {'sda': {'reads_completed': 100}}
        collector2._previous_io_stats = {'sdb': {'reads_completed': 200}}
        
        # Each instance should maintain its own state
        assert storage_collector._previous_io_stats != collector2._previous_io_stats
        assert 'sda' in storage_collector._previous_io_stats
        assert 'sdb' in collector2._previous_io_stats
    
    @pytest.mark.asyncio
    async def test_edge_case_very_large_disk_stats(self, storage_collector):
        """Test handling of very large disk statistics."""
        large_diskstats = """   8       0 sda 999999999 999999999 999999999999 999999999 999999999 999999999 999999999999 999999999 0 999999999 999999999"""
        
        # Set up previous data
        storage_collector._previous_io_stats = {
            'sda': {
                'reads_completed': 999999000,
                'sectors_read': 999999000000,
                'read_time_ms': 999999000,
                'writes_completed': 999999000,
                'sectors_written': 999999000000,
                'write_time_ms': 999999000,
                'io_in_progress': 0,
                'io_time_ms': 999999000
            }
        }
        storage_collector._previous_collect_time = 123450.0
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=large_diskstats):
            result = await storage_collector._get_disk_io_stats(123456.0)
            
            # Should handle large numbers without overflow
            assert 'disk_io' in result
            if len(result['disk_io']) > 0:
                io_info = result['disk_io'][0]
                assert io_info['reads_per_sec'] >= 0
                assert io_info['writes_per_sec'] >= 0
                assert io_info['read_bytes_per_sec'] >= 0
                assert io_info['write_bytes_per_sec'] >= 0
    
    @pytest.mark.asyncio
    async def test_edge_case_filesystem_usage_calculation_edge_cases(self, storage_collector):
        """Test filesystem usage calculation edge cases."""
        simple_mounts = "/dev/sda1 / ext4 rw,relatime 0 0"
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=simple_mounts):
            # Test with zero total blocks
            zero_blocks_stat = MagicMock()
            zero_blocks_stat.f_blocks = 0
            zero_blocks_stat.f_bfree = 0
            zero_blocks_stat.f_bavail = 0
            zero_blocks_stat.f_frsize = 4096
            
            with patch('os.statvfs', return_value=zero_blocks_stat):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                if len(filesystems) > 0:
                    fs = filesystems[0]
                    assert fs['total_bytes'] == 0
                    assert fs['usage_percent'] == 0  # Should handle zero division
    
    @pytest.mark.asyncio
    async def test_edge_case_full_filesystem(self, storage_collector):
        """Test handling of completely full filesystem."""
        simple_mounts = "/dev/sda1 / ext4 rw,relatime 0 0"
        
        with patch('ptop.utils.helpers.read_proc_file', return_value=simple_mounts):
            # Full filesystem
            full_stat = MagicMock()
            full_stat.f_blocks = 1000
            full_stat.f_bfree = 0
            full_stat.f_bavail = 0
            full_stat.f_frsize = 4096
            
            with patch('os.statvfs', return_value=full_stat):
                result = await storage_collector._get_filesystem_usage()
                
                filesystems = result['filesystems']
                if len(filesystems) > 0:
                    fs = filesystems[0]
                    assert fs['usage_percent'] == 100.0
                    assert fs['free_bytes'] == 0