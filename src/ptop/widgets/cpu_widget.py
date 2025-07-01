"""CPU monitoring widget."""

from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from rich.text import Text
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from typing import Dict, Any

from .base import BaseMetricWidget
from ..utils.formatters import format_percentage, format_frequency, format_load_average


class CPUWidget(BaseMetricWidget):
    """Widget for displaying CPU metrics."""
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.console = Console()
    
    def render(self) -> Panel:
        """Render the CPU widget."""
        if not self.data:
            return Panel("Loading CPU data...", title="CPU")
        
        # Create CPU usage display
        content = []
        
        # Overall CPU usage
        overall_usage = self.data.get('overall_cpu_usage', 0.0)
        content.append(f"Overall: {format_percentage(overall_usage)}")
        
        # Create progress bar for overall usage
        bar_chars = '█' * int(overall_usage / 100 * 30)
        empty_chars = '░' * (30 - len(bar_chars))
        content.append(f"  [{bar_chars}{empty_chars}]")
        
        # Per-core usage
        per_core = self.data.get('per_core_usage', {})
        if per_core:
            content.append("")
            content.append("Per Core:")
            for core_name, usage in sorted(per_core.items()):
                bar_chars = '█' * int(usage / 100 * 20)
                empty_chars = '░' * (20 - len(bar_chars))
                content.append(f"  {core_name}: {format_percentage(usage)} [{bar_chars}{empty_chars}]")
        
        # Load averages
        load_1min = self.data.get('load_1min')
        load_5min = self.data.get('load_5min')
        load_15min = self.data.get('load_15min')
        
        if load_1min is not None:
            content.append("")
            content.append("Load Average:")
            content.append(f"  1min: {format_load_average(load_1min)}")
            content.append(f"  5min: {format_load_average(load_5min)}")
            content.append(f"  15min: {format_load_average(load_15min)}")
        
        # CPU info
        model_name = self.data.get('model_name')
        cpu_count = self.data.get('cpu_count')
        avg_freq = self.data.get('avg_frequency_mhz')
        
        if model_name:
            content.append("")
            content.append("CPU Info:")
            if cpu_count:
                content.append(f"  Cores: {cpu_count}")
            content.append(f"  Model: {model_name}")
            if avg_freq:
                content.append(f"  Avg Freq: {format_frequency(avg_freq * 1e6)}")
        
        # Join content and create panel
        content_text = "\n".join(content)
        
        # Color based on usage
        title_color = "green"
        if overall_usage > 70:
            title_color = "yellow"
        if overall_usage > 90:
            title_color = "red"
        
        return Panel(
            content_text,
            title=f"[{title_color}]CPU[/{title_color}]",
            border_style=title_color
        )