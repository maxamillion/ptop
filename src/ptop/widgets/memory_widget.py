"""Memory monitoring widget."""

from textual.widget import Widget
from rich.panel import Panel
from typing import Dict, Any

from .base import BaseMetricWidget
from ..utils.formatters import format_bytes, format_percentage


class MemoryWidget(BaseMetricWidget):
    """Widget for displaying memory metrics."""
    
    def render(self) -> Panel:
        """Render the memory widget."""
        if not self.data:
            return Panel("Loading memory data...", title="Memory")
        
        content = []
        
        # Physical Memory
        mem_total = self.data.get('mem_total', 0)
        mem_used = self.data.get('mem_used', 0)
        mem_available = self.data.get('mem_available', 0)
        mem_used_percent = self.data.get('mem_used_percent', 0)
        
        if mem_total > 0:
            content.append("Physical Memory:")
            content.append(f"  Total: {format_bytes(mem_total)}")
            content.append(f"  Used:  {format_bytes(mem_used)} ({format_percentage(mem_used_percent)})")
            content.append(f"  Avail: {format_bytes(mem_available)}")
            
            # Memory usage bar
            bar_chars = '█' * int(mem_used_percent / 100 * 30)
            empty_chars = '░' * (30 - len(bar_chars))
            content.append(f"  Usage: [{bar_chars}{empty_chars}]")
        
        # Buffers and Cache
        buffers = self.data.get('buffers', 0)
        cached = self.data.get('cached', 0)
        buffers_percent = self.data.get('buffers_percent', 0)
        cached_percent = self.data.get('cached_percent', 0)
        
        if buffers > 0 or cached > 0:
            content.append("")
            content.append("Buffers & Cache:")
            if buffers > 0:
                content.append(f"  Buffers: {format_bytes(buffers)} ({format_percentage(buffers_percent)})")
            if cached > 0:
                content.append(f"  Cached:  {format_bytes(cached)} ({format_percentage(cached_percent)})")
        
        # Swap Memory
        swap_total = self.data.get('swap_total', 0)
        swap_used = self.data.get('swap_used', 0)
        swap_used_percent = self.data.get('swap_used_percent', 0)
        
        if swap_total > 0:
            content.append("")
            content.append("Swap Memory:")
            content.append(f"  Total: {format_bytes(swap_total)}")
            content.append(f"  Used:  {format_bytes(swap_used)} ({format_percentage(swap_used_percent)})")
            
            # Swap usage bar
            bar_chars = '█' * int(swap_used_percent / 100 * 30)
            empty_chars = '░' * (30 - len(bar_chars))
            content.append(f"  Usage: [{bar_chars}{empty_chars}]")
        else:
            content.append("")
            content.append("Swap: Disabled")
        
        # Memory pressure indicators
        active_percent = self.data.get('active_percent', 0)
        dirty_percent = self.data.get('dirty_percent', 0)
        
        if active_percent > 0 or dirty_percent > 0:
            content.append("")
            content.append("Memory Activity:")
            if active_percent > 0:
                content.append(f"  Active: {format_percentage(active_percent)}")
            if dirty_percent > 0:
                content.append(f"  Dirty:  {format_percentage(dirty_percent)}")
        
        # Join content and create panel
        content_text = "\n".join(content)
        
        # Color based on usage
        title_color = "green"
        if mem_used_percent > 80:
            title_color = "yellow"
        if mem_used_percent > 95:
            title_color = "red"
        
        return Panel(
            content_text,
            title=f"[{title_color}]Memory[/{title_color}]",
            border_style=title_color
        )