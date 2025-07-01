"""Storage monitoring widget."""

from textual.widget import Widget
from rich.panel import Panel
from typing import Dict, Any

from .base import BaseMetricWidget
from ..utils.formatters import format_bytes, format_percentage


class StorageWidget(BaseMetricWidget):
    """Widget for displaying storage and I/O metrics."""
    
    def render(self) -> Panel:
        """Render the storage widget."""
        if not self.data:
            return Panel("Loading storage data...", title="Storage")
        
        content = []
        
        # Filesystem usage
        filesystems = self.data.get('filesystems', [])
        if filesystems:
            content.append("Filesystem Usage:")
            for fs in filesystems[:5]:  # Show top 5 filesystems
                mount_point = fs['mount_point']
                if len(mount_point) > 15:
                    mount_point = mount_point[:12] + "..."
                
                usage_percent = fs['usage_percent']
                used_bytes = fs['used_bytes']
                total_bytes = fs['total_bytes']
                
                # Create usage bar
                bar_chars = '█' * int(usage_percent / 100 * 20)
                empty_chars = '░' * (20 - len(bar_chars))
                
                content.append(f"  {mount_point:15s} [{bar_chars}{empty_chars}]")
                content.append(f"  {format_percentage(usage_percent)} "
                             f"({format_bytes(used_bytes)}/{format_bytes(total_bytes)})")
                content.append("")
        
        # Disk I/O statistics
        disk_io = self.data.get('disk_io', [])
        if disk_io:
            content.append("Disk I/O Activity:")
            
            for io in disk_io[:3]:  # Show top 3 active disks
                device = io['device']
                reads_per_sec = io['reads_per_sec']
                writes_per_sec = io['writes_per_sec']
                read_bytes_per_sec = io['read_bytes_per_sec']
                write_bytes_per_sec = io['write_bytes_per_sec']
                utilization = io['utilization_percent']
                
                content.append(f"  {device}:")
                content.append(f"    R: {reads_per_sec:>6.1f}/s ({format_bytes(read_bytes_per_sec)}/s)")
                content.append(f"    W: {writes_per_sec:>6.1f}/s ({format_bytes(write_bytes_per_sec)}/s)")
                content.append(f"    Util: {format_percentage(utilization)}")
                content.append("")
        
        if not content:
            content.append("No storage data available")
        
        # Join content and create panel
        content_text = "\n".join(content)
        
        # Color based on highest filesystem usage
        title_color = "green"
        if filesystems:
            max_usage = max((fs['usage_percent'] for fs in filesystems), default=0)
            if max_usage > 80:
                title_color = "yellow"
            if max_usage > 95:
                title_color = "red"
        
        return Panel(
            content_text,
            title=f"[{title_color}]Storage[/{title_color}]",
            border_style=title_color
        )