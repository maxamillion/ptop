"""Process monitoring widget."""

from textual.widget import Widget
from textual.widgets import DataTable
from rich.panel import Panel
from rich.text import Text
from typing import Dict, Any, List

from .base import BaseMetricWidget
from ..utils.formatters import format_bytes, format_percentage


class ProcessWidget(BaseMetricWidget):
    """Widget for displaying process information."""
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.show_details = True
    
    def render(self) -> Panel:
        """Render the process widget."""
        if not self.data:
            return Panel("Loading process data...", title="Processes")
        
        content = []
        
        # Process summary
        summary = self.data.get('process_summary', {})
        total_processes = self.data.get('total_processes', 0)
        
        if summary:
            content.append(f"Total: {total_processes}")
            content.append(f"Running: {summary.get('running', 0)} | "
                          f"Sleeping: {summary.get('sleeping', 0)} | "
                          f"Stopped: {summary.get('stopped', 0)}")
            content.append(f"Threads: {summary.get('total_threads', 0)} | "
                          f"Avg CPU: {format_percentage(summary.get('avg_cpu_usage', 0))}")
            content.append("")
        
        # Process table header
        if self.show_details:
            content.append("PID      CPU%   MEM%   RSS      THREADS  STATE  NAME")
            content.append("─" * 65)
            
            # Process list
            processes = self.data.get('processes', [])
            for process in processes[:15]:  # Show top 15 processes
                pid_str = f"{process.pid:>8}"
                cpu_str = f"{process.cpu_percent:>6.1f}"
                mem_str = f"{process.memory_percent:>6.1f}"
                rss_str = f"{format_bytes(process.memory_rss):>8}"
                threads_str = f"{process.threads:>8}"
                state_str = f"{process.state:>5}"
                
                # Truncate name if too long
                name = process.name
                if len(name) > 15:
                    name = name[:12] + "..."
                
                line = f"{pid_str} {cpu_str} {mem_str} {rss_str} {threads_str} {state_str}  {name}"
                content.append(line)
        else:
            # Simplified view
            content.append("Top CPU Consumers:")
            processes = self.data.get('processes', [])
            for i, process in enumerate(processes[:10]):
                content.append(f"{i+1:2d}. {process.name:20s} {format_percentage(process.cpu_percent):>6}")
        
        # Join content and create panel
        content_text = "\n".join(content)
        
        # Color based on load
        title_color = "green"
        if summary.get('running', 0) > 10:
            title_color = "yellow"
        if summary.get('running', 0) > 20:
            title_color = "red"
        
        return Panel(
            content_text,
            title=f"[{title_color}]Processes[/{title_color}]",
            border_style=title_color
        )