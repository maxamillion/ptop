"""Storage and I/O metrics collector."""

import os
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseCollector
from ..utils.helpers import read_proc_file


class StorageCollector(BaseCollector):
    """Collector for storage and disk I/O metrics."""
    
    def __init__(self) -> None:
        self._previous_io_stats: Dict[str, Dict[str, int]] = {}
        self._previous_collect_time = 0.0
    
    @property
    def name(self) -> str:
        return "storage"
    
    @property
    def update_interval(self) -> float:
        return 2.0
    
    async def collect(self) -> Dict[str, Any]:
        """Collect storage and I/O metrics.
        
        Returns:
            Dictionary containing storage metrics.
        """
        current_time = asyncio.get_event_loop().time()
        
        metrics = {}
        
        # Get filesystem usage
        metrics.update(await self._get_filesystem_usage())
        
        # Get disk I/O statistics
        metrics.update(await self._get_disk_io_stats(current_time))
        
        # Update previous collect time
        self._previous_collect_time = current_time
        
        return metrics
    
    async def _get_filesystem_usage(self) -> Dict[str, Any]:
        """Get filesystem usage information."""
        filesystems = []
        
        # Read /proc/mounts to get mounted filesystems
        mounts_content = read_proc_file('/proc/mounts')
        if not mounts_content:
            return {'filesystems': filesystems}
        
        # Filter for real filesystems (exclude virtual ones)
        real_fs_types = {
            'ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'reiserfs', 'jfs',
            'ntfs', 'vfat', 'exfat', 'f2fs', 'zfs'
        }
        
        for line in mounts_content.split('\n'):
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 3:
                continue
            
            device = parts[0]
            mount_point = parts[1]
            fs_type = parts[2]
            
            # Skip virtual filesystems
            if fs_type not in real_fs_types:
                continue
            
            # Skip special mount points
            if mount_point.startswith('/proc') or mount_point.startswith('/sys'):
                continue
            
            try:
                # Get filesystem statistics
                statvfs = os.statvfs(mount_point)
                
                total_bytes = statvfs.f_blocks * statvfs.f_frsize
                free_bytes = statvfs.f_bavail * statvfs.f_frsize
                used_bytes = total_bytes - (statvfs.f_bfree * statvfs.f_frsize)
                
                # Calculate usage percentage
                usage_percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0
                
                filesystem_info = {
                    'device': device,
                    'mount_point': mount_point,
                    'fs_type': fs_type,
                    'total_bytes': total_bytes,
                    'used_bytes': used_bytes,
                    'free_bytes': free_bytes,
                    'usage_percent': usage_percent
                }
                
                filesystems.append(filesystem_info)
                
            except (OSError, IOError):
                # Permission denied or filesystem issue
                continue
        
        # Sort by usage percentage (descending)
        filesystems.sort(key=lambda x: x['usage_percent'], reverse=True)
        
        return {'filesystems': filesystems}
    
    async def _get_disk_io_stats(self, current_time: float) -> Dict[str, Any]:
        """Get disk I/O statistics from /proc/diskstats."""
        diskstats_content = read_proc_file('/proc/diskstats')
        if not diskstats_content:
            return {'disk_io': []}
        
        current_stats = {}
        io_metrics = []
        
        for line in diskstats_content.split('\n'):
            if not line.strip():
                continue
            
            fields = line.split()
            if len(fields) < 14:
                continue
            
            # Extract disk statistics
            major = int(fields[0])
            minor = int(fields[1])
            device = fields[2]
            
            # Skip partition devices (only show main devices)
            if any(device.endswith(str(i)) for i in range(10)):
                continue
            
            reads_completed = int(fields[3])
            reads_merged = int(fields[4])
            sectors_read = int(fields[5])
            read_time_ms = int(fields[6])
            
            writes_completed = int(fields[7])
            writes_merged = int(fields[8])
            sectors_written = int(fields[9])
            write_time_ms = int(fields[10])
            
            io_in_progress = int(fields[11])
            io_time_ms = int(fields[12])
            weighted_io_time_ms = int(fields[13])
            
            current_stats[device] = {
                'reads_completed': reads_completed,
                'sectors_read': sectors_read,
                'read_time_ms': read_time_ms,
                'writes_completed': writes_completed,
                'sectors_written': sectors_written,
                'write_time_ms': write_time_ms,
                'io_in_progress': io_in_progress,
                'io_time_ms': io_time_ms
            }
        
        # Calculate rates if we have previous data
        if self._previous_io_stats and self._previous_collect_time > 0:
            time_delta = current_time - self._previous_collect_time
            
            for device, current in current_stats.items():
                if device in self._previous_io_stats and time_delta > 0:
                    prev = self._previous_io_stats[device]
                    
                    # Calculate rates (per second)
                    reads_per_sec = (current['reads_completed'] - prev['reads_completed']) / time_delta
                    writes_per_sec = (current['writes_completed'] - prev['writes_completed']) / time_delta
                    
                    # Calculate throughput (bytes per second, assuming 512 byte sectors)
                    read_bytes_per_sec = (current['sectors_read'] - prev['sectors_read']) * 512 / time_delta
                    write_bytes_per_sec = (current['sectors_written'] - prev['sectors_written']) * 512 / time_delta
                    
                    # Calculate average I/O wait time
                    read_time_delta = current['read_time_ms'] - prev['read_time_ms']
                    write_time_delta = current['write_time_ms'] - prev['write_time_ms']
                    read_count_delta = current['reads_completed'] - prev['reads_completed']
                    write_count_delta = current['writes_completed'] - prev['writes_completed']
                    
                    avg_read_time = read_time_delta / read_count_delta if read_count_delta > 0 else 0
                    avg_write_time = write_time_delta / write_count_delta if write_count_delta > 0 else 0
                    
                    # Calculate utilization percentage
                    io_time_delta = current['io_time_ms'] - prev['io_time_ms']
                    utilization = (io_time_delta / (time_delta * 1000)) * 100
                    
                    io_info = {
                        'device': device,
                        'reads_per_sec': reads_per_sec,
                        'writes_per_sec': writes_per_sec,
                        'read_bytes_per_sec': read_bytes_per_sec,
                        'write_bytes_per_sec': write_bytes_per_sec,
                        'avg_read_time_ms': avg_read_time,
                        'avg_write_time_ms': avg_write_time,
                        'utilization_percent': min(100, utilization),
                        'io_in_progress': current['io_in_progress']
                    }
                    
                    io_metrics.append(io_info)
        
        # Store current stats for next calculation
        self._previous_io_stats = current_stats
        
        # Sort by utilization (descending)
        io_metrics.sort(key=lambda x: x['utilization_percent'], reverse=True)
        
        return {'disk_io': io_metrics}