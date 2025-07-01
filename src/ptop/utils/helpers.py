"""General helper functions for ptop."""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional


def read_proc_file(file_path: str) -> Optional[str]:
    """Safely read a /proc filesystem file.
    
    Args:
        file_path: Path to the proc file.
        
    Returns:
        File contents or None if unable to read.
    """
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except (IOError, OSError, PermissionError):
        return None


def parse_proc_stat_line(line: str) -> Dict[str, int]:
    """Parse a line from /proc/stat.
    
    Args:
        line: Line from /proc/stat.
        
    Returns:
        Dictionary with parsed CPU time values.
    """
    parts = line.split()
    if len(parts) < 8:
        return {}
    
    return {
        'user': int(parts[1]),
        'nice': int(parts[2]),
        'system': int(parts[3]),
        'idle': int(parts[4]),
        'iowait': int(parts[5]),
        'irq': int(parts[6]),
        'softirq': int(parts[7]),
        'steal': int(parts[8]) if len(parts) > 8 else 0,
        'guest': int(parts[9]) if len(parts) > 9 else 0,
        'guest_nice': int(parts[10]) if len(parts) > 10 else 0,
    }


def calculate_cpu_percentage(prev_times: Dict[str, int], 
                           curr_times: Dict[str, int]) -> float:
    """Calculate CPU usage percentage from time differences.
    
    Args:
        prev_times: Previous CPU time values.
        curr_times: Current CPU time values.
        
    Returns:
        CPU usage percentage (0-100).
    """
    if not prev_times or not curr_times:
        return 0.0
    
    prev_total = sum(prev_times.values())
    curr_total = sum(curr_times.values())
    total_diff = curr_total - prev_total
    
    if total_diff == 0:
        return 0.0
    
    prev_idle = prev_times.get('idle', 0) + prev_times.get('iowait', 0)
    curr_idle = curr_times.get('idle', 0) + curr_times.get('iowait', 0)
    idle_diff = curr_idle - prev_idle
    
    used_diff = total_diff - idle_diff
    return (used_diff / total_diff) * 100.0


def parse_meminfo(content: str) -> Dict[str, int]:
    """Parse /proc/meminfo content.
    
    Args:
        content: Content of /proc/meminfo.
        
    Returns:
        Dictionary with memory information in bytes.
    """
    meminfo = {}
    for line in content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Extract numeric value (remove 'kB' suffix)
            if value.endswith(' kB'):
                value = value[:-3]
            
            try:
                # Convert to bytes (from kB)
                meminfo[key] = int(value) * 1024
            except ValueError:
                continue
    
    return meminfo


def get_process_list() -> List[int]:
    """Get list of running process PIDs.
    
    Returns:
        List of process IDs.
    """
    try:
        return [int(d) for d in os.listdir('/proc') if d.isdigit()]
    except OSError:
        return []


async def run_command(command: List[str]) -> Optional[str]:
    """Run a system command asynchronously.
    
    Args:
        command: Command and arguments as list.
        
    Returns:
        Command output or None if failed.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        if process.returncode == 0:
            return stdout.decode('utf-8').strip()
    except Exception:
        pass
    return None