"""Memory metrics collector."""

import asyncio
from typing import Dict, Any, Optional
from .base import BaseCollector
from ..utils.helpers import read_proc_file, parse_meminfo


class MemoryCollector(BaseCollector):
    """Collector for memory usage and swap statistics."""
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def update_interval(self) -> float:
        return 1.0
    
    async def collect(self) -> Dict[str, Any]:
        """Collect memory metrics.
        
        Returns:
            Dictionary containing memory metrics.
        """
        metrics = {}
        
        # Get memory information
        metrics.update(await self._get_memory_info())
        
        # Get swap information
        metrics.update(await self._get_swap_info())
        
        # Calculate additional metrics
        metrics.update(await self._calculate_memory_metrics(metrics))
        
        return metrics
    
    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information from /proc/meminfo."""
        memory_info = {}
        
        meminfo_content = read_proc_file('/proc/meminfo')
        if not meminfo_content:
            return memory_info
        
        meminfo = parse_meminfo(meminfo_content)
        
        # Extract key memory metrics
        memory_info['mem_total'] = meminfo.get('MemTotal', 0)
        memory_info['mem_free'] = meminfo.get('MemFree', 0)
        memory_info['mem_available'] = meminfo.get('MemAvailable', 0)
        memory_info['buffers'] = meminfo.get('Buffers', 0)
        memory_info['cached'] = meminfo.get('Cached', 0)
        memory_info['slab'] = meminfo.get('Slab', 0)
        memory_info['sreclaimable'] = meminfo.get('SReclaimable', 0)
        memory_info['sunreclaim'] = meminfo.get('SUnreclaim', 0)
        
        # Active/Inactive memory
        memory_info['active'] = meminfo.get('Active', 0)
        memory_info['inactive'] = meminfo.get('Inactive', 0)
        memory_info['active_anon'] = meminfo.get('Active(anon)', 0)
        memory_info['inactive_anon'] = meminfo.get('Inactive(anon)', 0)
        memory_info['active_file'] = meminfo.get('Active(file)', 0)
        memory_info['inactive_file'] = meminfo.get('Inactive(file)', 0)
        
        # Dirty pages
        memory_info['dirty'] = meminfo.get('Dirty', 0)
        memory_info['writeback'] = meminfo.get('Writeback', 0)
        
        # Memory mapped
        memory_info['mapped'] = meminfo.get('Mapped', 0)
        memory_info['shmem'] = meminfo.get('Shmem', 0)
        
        return memory_info
    
    async def _get_swap_info(self) -> Dict[str, Any]:
        """Get swap information."""
        swap_info = {}
        
        meminfo_content = read_proc_file('/proc/meminfo')
        if not meminfo_content:
            return swap_info
        
        meminfo = parse_meminfo(meminfo_content)
        
        # Extract swap metrics
        swap_info['swap_total'] = meminfo.get('SwapTotal', 0)
        swap_info['swap_free'] = meminfo.get('SwapFree', 0)
        swap_info['swap_cached'] = meminfo.get('SwapCached', 0)
        
        return swap_info
    
    async def _calculate_memory_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived memory metrics."""
        calculated = {}
        
        mem_total = metrics.get('mem_total', 0)
        mem_free = metrics.get('mem_free', 0)
        mem_available = metrics.get('mem_available', 0)
        buffers = metrics.get('buffers', 0)
        cached = metrics.get('cached', 0)
        
        if mem_total > 0:
            # Calculate used memory (total - available)
            if mem_available > 0:
                mem_used = mem_total - mem_available
            else:
                # Fallback calculation if MemAvailable is not present
                mem_used = mem_total - mem_free - buffers - cached
            
            calculated['mem_used'] = max(0, mem_used)
            calculated['mem_used_percent'] = (mem_used / mem_total) * 100
            calculated['mem_available_percent'] = (mem_available / mem_total) * 100 if mem_available else 0
            
            # Buffer and cache percentages
            calculated['buffers_percent'] = (buffers / mem_total) * 100
            calculated['cached_percent'] = (cached / mem_total) * 100
        
        # Swap calculations
        swap_total = metrics.get('swap_total', 0)
        swap_free = metrics.get('swap_free', 0)
        
        if swap_total > 0:
            swap_used = swap_total - swap_free
            calculated['swap_used'] = swap_used
            calculated['swap_used_percent'] = (swap_used / swap_total) * 100
        else:
            calculated['swap_used'] = 0
            calculated['swap_used_percent'] = 0
        
        # Memory pressure indicators
        active = metrics.get('active', 0)
        inactive = metrics.get('inactive', 0)
        dirty = metrics.get('dirty', 0)
        
        if mem_total > 0:
            calculated['active_percent'] = (active / mem_total) * 100
            calculated['inactive_percent'] = (inactive / mem_total) * 100
            calculated['dirty_percent'] = (dirty / mem_total) * 100
        
        return calculated