"""Process metrics collector."""

import os
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from .base import BaseCollector
from ..utils.helpers import read_proc_file, get_process_list


class ProcessInfo:
    """Container for process information."""
    
    def __init__(self, pid: int):
        self.pid = pid
        self.name = ""
        self.cmdline = ""
        self.state = ""
        self.ppid = 0
        self.cpu_percent = 0.0
        self.memory_percent = 0.0
        self.memory_rss = 0
        self.memory_vms = 0
        self.threads = 0
        self.create_time = 0
        self.user = ""
        self.nice = 0


class ProcessCollector(BaseCollector):
    """Collector for process information and statistics."""
    
    def __init__(self) -> None:
        self._previous_cpu_times: Dict[int, Tuple[float, float]] = {}
        self._previous_collect_time = 0.0
        self._system_memory_total = 0
    
    @property
    def name(self) -> str:
        return "process"
    
    @property
    def update_interval(self) -> float:
        return 2.0
    
    async def collect(self) -> Dict[str, Any]:
        """Collect process metrics.
        
        Returns:
            Dictionary containing process metrics.
        """
        current_time = asyncio.get_event_loop().time()
        
        # Get system memory total for percentage calculations
        if self._system_memory_total == 0:
            await self._get_system_memory_total()
        
        # Get all running processes
        process_list = get_process_list()
        processes = []
        
        for pid in process_list:
            try:
                process_info = await self._get_process_info(pid, current_time)
                if process_info:
                    processes.append(process_info)
            except (OSError, IOError, PermissionError):
                # Process may have disappeared or we don't have permission
                continue
        
        # Sort processes by CPU usage (descending)
        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        
        # Update previous collect time
        self._previous_collect_time = current_time
        
        metrics = {
            'processes': processes[:50],  # Top 50 processes
            'total_processes': len(process_list),
            'process_summary': self._get_process_summary(processes)
        }
        
        return metrics
    
    async def _get_system_memory_total(self) -> None:
        """Get total system memory for percentage calculations."""
        meminfo_content = read_proc_file('/proc/meminfo')
        if meminfo_content:
            for line in meminfo_content.split('\n'):
                if line.startswith('MemTotal:'):
                    # Extract value in kB and convert to bytes
                    value = line.split()[1]
                    self._system_memory_total = int(value) * 1024
                    break
    
    async def _get_process_info(self, pid: int, current_time: float) -> Optional[ProcessInfo]:
        """Get information for a specific process."""
        try:
            process = ProcessInfo(pid)
            
            # Read /proc/[pid]/stat
            stat_content = read_proc_file(f'/proc/{pid}/stat')
            if stat_content:
                await self._parse_stat(process, stat_content, current_time)
            
            # Read /proc/[pid]/status
            status_content = read_proc_file(f'/proc/{pid}/status')
            if status_content:
                await self._parse_status(process, status_content)
            
            # Read /proc/[pid]/cmdline
            cmdline_content = read_proc_file(f'/proc/{pid}/cmdline')
            if cmdline_content:
                # Replace null bytes with spaces
                process.cmdline = cmdline_content.replace('\x00', ' ').strip()
            
            # Get process owner
            try:
                stat_info = os.stat(f'/proc/{pid}')
                process.user = str(stat_info.st_uid)  # Could be enhanced to resolve username
            except (OSError, IOError):
                process.user = "unknown"
            
            return process
            
        except Exception:
            return None
    
    async def _parse_stat(self, process: ProcessInfo, stat_content: str, current_time: float) -> None:
        """Parse /proc/[pid]/stat file."""
        fields = stat_content.split()
        if len(fields) < 52:
            return
        
        # Extract relevant fields
        process.name = fields[1].strip('()')
        process.state = fields[2]
        process.ppid = int(fields[3])
        process.nice = int(fields[18])
        process.threads = int(fields[19])
        
        # CPU times (in clock ticks)
        utime = int(fields[13])  # User time
        stime = int(fields[14])  # System time
        total_time = utime + stime
        
        # Calculate CPU percentage
        if process.pid in self._previous_cpu_times and self._previous_collect_time > 0:
            prev_total, prev_time = self._previous_cpu_times[process.pid]
            time_delta = current_time - prev_time
            cpu_delta = total_time - prev_total
            
            if time_delta > 0:
                # Convert clock ticks to seconds (assuming 100 ticks per second)
                cpu_seconds = cpu_delta / 100.0
                process.cpu_percent = (cpu_seconds / time_delta) * 100.0
        
        # Store current values for next calculation
        self._previous_cpu_times[process.pid] = (total_time, current_time)
        
        # Memory information (in pages, convert to bytes)
        page_size = 4096  # Assume 4KB pages
        process.memory_rss = int(fields[23]) * page_size
        process.memory_vms = int(fields[22]) * page_size
        
        # Calculate memory percentage
        if self._system_memory_total > 0:
            process.memory_percent = (process.memory_rss / self._system_memory_total) * 100
    
    async def _parse_status(self, process: ProcessInfo, status_content: str) -> None:
        """Parse /proc/[pid]/status file for additional information."""
        for line in status_content.split('\n'):
            if line.startswith('VmRSS:'):
                # Get RSS memory in kB
                parts = line.split()
                if len(parts) >= 2:
                    process.memory_rss = int(parts[1]) * 1024  # Convert to bytes
            elif line.startswith('VmSize:'):
                # Get virtual memory size in kB
                parts = line.split()
                if len(parts) >= 2:
                    process.memory_vms = int(parts[1]) * 1024  # Convert to bytes
            elif line.startswith('Threads:'):
                # Get thread count
                parts = line.split()
                if len(parts) >= 2:
                    process.threads = int(parts[1])
    
    def _get_process_summary(self, processes: List[ProcessInfo]) -> Dict[str, Any]:
        """Generate summary statistics for processes."""
        if not processes:
            return {}
        
        running = sum(1 for p in processes if p.state == 'R')
        sleeping = sum(1 for p in processes if p.state == 'S')
        stopped = sum(1 for p in processes if p.state in ['T', 'Z'])
        
        total_memory = sum(p.memory_rss for p in processes)
        total_threads = sum(p.threads for p in processes)
        
        return {
            'running': running,
            'sleeping': sleeping,
            'stopped': stopped,
            'total_memory_usage': total_memory,
            'total_threads': total_threads,
            'avg_cpu_usage': sum(p.cpu_percent for p in processes) / len(processes) if processes else 0
        }