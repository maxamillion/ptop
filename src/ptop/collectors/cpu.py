"""CPU metrics collector."""

import asyncio
from typing import Dict, Any, List, Optional
from .base import BaseCollector
from ..utils.helpers import read_proc_file, parse_proc_stat_line, calculate_cpu_percentage


class CPUCollector(BaseCollector):
    """Collector for CPU usage, load averages, and related metrics."""
    
    def __init__(self) -> None:
        self._previous_cpu_times: Dict[str, Dict[str, int]] = {}
        self._cpu_count: Optional[int] = None
    
    @property
    def name(self) -> str:
        return "cpu"
    
    @property
    def update_interval(self) -> float:
        return 1.0
    
    async def collect(self) -> Dict[str, Any]:
        """Collect CPU metrics.
        
        Returns:
            Dictionary containing CPU metrics.
        """
        metrics = {}
        
        # Get basic CPU info
        metrics.update(await self._get_cpu_info())
        
        # Get CPU usage statistics
        metrics.update(await self._get_cpu_usage())
        
        # Get load averages
        metrics.update(await self._get_load_averages())
        
        # Get CPU frequencies (if available)
        metrics.update(await self._get_cpu_frequencies())
        
        return metrics
    
    async def _get_cpu_info(self) -> Dict[str, Any]:
        """Get basic CPU information."""
        cpu_info = {}
        
        cpuinfo_content = read_proc_file('/proc/cpuinfo')
        if cpuinfo_content:
            lines = cpuinfo_content.split('\n')
            cpu_count = 0
            model_name = None
            
            for line in lines:
                if line.startswith('processor'):
                    cpu_count = int(line.split(':')[1].strip()) + 1
                elif line.startswith('model name') and model_name is None:
                    model_name = line.split(':', 1)[1].strip()
            
            cpu_info['cpu_count'] = cpu_count
            cpu_info['model_name'] = model_name or 'Unknown'
            self._cpu_count = cpu_count
        
        return cpu_info
    
    async def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage statistics."""
        cpu_usage = {}
        
        stat_content = read_proc_file('/proc/stat')
        if not stat_content:
            return cpu_usage
        
        lines = stat_content.split('\n')
        current_cpu_times = {}
        
        for line in lines:
            if line.startswith('cpu'):
                parts = line.split()
                cpu_name = parts[0]
                
                # Parse CPU times
                cpu_times = parse_proc_stat_line(line)
                if cpu_times:
                    current_cpu_times[cpu_name] = cpu_times
        
        # Calculate CPU usage percentages
        cpu_percentages = {}
        for cpu_name, current_times in current_cpu_times.items():
            if cpu_name in self._previous_cpu_times:
                prev_times = self._previous_cpu_times[cpu_name]
                percentage = calculate_cpu_percentage(prev_times, current_times)
                cpu_percentages[cpu_name] = round(percentage, 1)
            else:
                cpu_percentages[cpu_name] = 0.0
        
        # Store current times for next calculation
        self._previous_cpu_times = current_cpu_times
        
        cpu_usage['cpu_percentages'] = cpu_percentages
        
        # Calculate overall CPU usage
        if 'cpu' in cpu_percentages:
            cpu_usage['overall_cpu_usage'] = cpu_percentages['cpu']
        
        # Calculate per-core usage
        per_core_usage = {}
        for cpu_name, percentage in cpu_percentages.items():
            if cpu_name.startswith('cpu') and cpu_name != 'cpu':
                core_num = cpu_name[3:]  # Remove 'cpu' prefix
                per_core_usage[f'core_{core_num}'] = percentage
        
        cpu_usage['per_core_usage'] = per_core_usage
        
        return cpu_usage
    
    async def _get_load_averages(self) -> Dict[str, Any]:
        """Get system load averages."""
        load_info = {}
        
        loadavg_content = read_proc_file('/proc/loadavg')
        if loadavg_content:
            parts = loadavg_content.split()
            if len(parts) >= 3:
                load_info['load_1min'] = float(parts[0])
                load_info['load_5min'] = float(parts[1])
                load_info['load_15min'] = float(parts[2])
                
                # Calculate load percentage based on CPU count
                if self._cpu_count:
                    load_info['load_1min_percent'] = (load_info['load_1min'] / self._cpu_count) * 100
                    load_info['load_5min_percent'] = (load_info['load_5min'] / self._cpu_count) * 100
                    load_info['load_15min_percent'] = (load_info['load_15min'] / self._cpu_count) * 100
        
        return load_info
    
    async def _get_cpu_frequencies(self) -> Dict[str, Any]:
        """Get CPU frequencies (if available)."""
        freq_info = {}
        
        try:
            # Try to read CPU frequency information
            freq_content = read_proc_file('/proc/cpuinfo')
            if freq_content:
                lines = freq_content.split('\n')
                frequencies = []
                
                for line in lines:
                    if line.startswith('cpu MHz'):
                        freq_str = line.split(':', 1)[1].strip()
                        try:
                            freq_mhz = float(freq_str)
                            frequencies.append(freq_mhz)
                        except ValueError:
                            continue
                
                if frequencies:
                    freq_info['cpu_frequencies_mhz'] = frequencies
                    freq_info['avg_frequency_mhz'] = sum(frequencies) / len(frequencies)
        except Exception:
            # Frequency information not available
            pass
        
        return freq_info