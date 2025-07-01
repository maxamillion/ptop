"""Utility functions for formatting system metrics data."""

from typing import Union


def format_bytes(bytes_value: Union[int, float]) -> str:
    """Format bytes value into human-readable string.
    
    Args:
        bytes_value: Number of bytes.
        
    Returns:
        Formatted string (e.g., "1.5 GB").
    """
    if bytes_value is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            if unit == 'B':
                return f"{int(bytes_value)} {unit}"
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} EB"


def format_percentage(value: Union[int, float], precision: int = 1) -> str:
    """Format percentage value.
    
    Args:
        value: Percentage value (0-100).
        precision: Number of decimal places.
        
    Returns:
        Formatted percentage string.
    """
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}%"


def format_frequency(hz_value: Union[int, float]) -> str:
    """Format frequency value into human-readable string.
    
    Args:
        hz_value: Frequency in Hz.
        
    Returns:
        Formatted string (e.g., "2.4 GHz").
    """
    if hz_value is None:
        return "N/A"
    
    if hz_value >= 1e9:
        return f"{hz_value / 1e9:.1f} GHz"
    elif hz_value >= 1e6:
        return f"{hz_value / 1e6:.0f} MHz"
    elif hz_value >= 1e3:
        return f"{hz_value / 1e3:.0f} KHz"
    else:
        return f"{hz_value:.0f} Hz"


def format_uptime(seconds: Union[int, float]) -> str:
    """Format uptime in seconds to human-readable string.
    
    Args:
        seconds: Uptime in seconds.
        
    Returns:
        Formatted uptime string.
    """
    if seconds is None:
        return "N/A"
    
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def format_load_average(load_avg: float) -> str:
    """Format load average with appropriate precision.
    
    Args:
        load_avg: Load average value.
        
    Returns:
        Formatted load average string.
    """
    if load_avg is None:
        return "N/A"
    return f"{load_avg:.2f}"