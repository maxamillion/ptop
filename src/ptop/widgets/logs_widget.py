"""System logs monitoring widget."""

from textual.widget import Widget
from rich.panel import Panel
from typing import Dict, Any

from .base import BaseMetricWidget


class LogsWidget(BaseMetricWidget):
    """Widget for displaying system log information."""
    
    def render(self) -> Panel:
        """Render the logs widget."""
        if not self.data:
            return Panel("Loading log data...", title="System Logs")
        
        content = []
        
        # Log statistics
        log_stats = self.data.get('log_statistics', {})
        if log_stats:
            total_entries = log_stats.get('total_entries', 0)
            error_entries = log_stats.get('error_entries', 0)
            recent_errors = log_stats.get('recent_errors', 0)
            
            content.append(f"Total: {total_entries} | Errors: {error_entries} | Recent: {recent_errors}")
            content.append("")
        
        # Recent error logs
        error_logs = self.data.get('error_logs', [])
        if error_logs:
            content.append("Recent Errors/Warnings:")
            for log in error_logs[-5:]:  # Show last 5 errors
                timestamp = log.timestamp.strftime('%H:%M:%S')
                level = log.level[:4]  # Truncate level
                source = log.source[:10] if len(log.source) > 10 else log.source
                
                # Truncate message if too long
                message = log.message
                if len(message) > 40:
                    message = message[:37] + "..."
                
                content.append(f"  {timestamp} {level:4s} {source:10s} {message}")
            content.append("")
        
        # Top log sources
        if log_stats and 'top_sources' in log_stats:
            top_sources = log_stats['top_sources']
            if top_sources:
                content.append("Top Sources:")
                for source, count in list(top_sources.items())[:3]:
                    source_display = source[:15] if len(source) > 15 else source
                    content.append(f"  {source_display:15s} {count:>3d}")
                content.append("")
        
        # Log level breakdown
        if log_stats and 'level_counts' in log_stats:
            level_counts = log_stats['level_counts']
            if level_counts:
                content.append("Log Levels:")
                for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
                    content.append(f"  {level:8s} {count:>3d}")
        
        if not content:
            content.append("No log data available")
        
        # Join content and create panel
        content_text = "\n".join(content)
        
        # Color based on recent errors
        title_color = "green"
        if log_stats:
            recent_errors = log_stats.get('recent_errors', 0)
            error_entries = log_stats.get('error_entries', 0)
            
            if recent_errors > 0:
                title_color = "yellow"
            if recent_errors > 5 or error_entries > 20:
                title_color = "red"
        
        return Panel(
            content_text,
            title=f"[{title_color}]System Logs[/{title_color}]",
            border_style=title_color
        )