"""Main Textual application for ptop."""

import asyncio
from typing import Dict, Any
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static

from .config.settings import PtopSettings
from .collectors.cpu import CPUCollector
from .collectors.memory import MemoryCollector
from .collectors.process import ProcessCollector
from .collectors.storage import StorageCollector
from .collectors.logs import LogCollector
from .widgets.cpu_widget import CPUWidget
from .widgets.memory_widget import MemoryWidget
from .widgets.process_widget import ProcessWidget
from .widgets.storage_widget import StorageWidget
from .widgets.logs_widget import LogsWidget


class PtopApp(App):
    """Main ptop application."""
    
    CSS = """
    .metric-container {
        border: solid $primary;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    .cpu-widget {
        height: 8;
    }
    
    .memory-widget {
        height: 6;
    }
    
    .storage-widget {
        height: 6;
    }
    
    .logs-widget {
        height: 8;
    }
    
    .process-widget {
        height: 1fr;
        min-height: 10;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("h", "help", "Help"),
    ]
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = PtopSettings.load_from_file()
        self.collectors: Dict[str, Any] = {}
        self.update_tasks: Dict[str, asyncio.Task] = {}
        self._initialize_collectors()
    
    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header()
        
        with Container():
            with Horizontal():
                with Vertical():
                    yield CPUWidget(classes="metric-container cpu-widget", id="cpu-widget")
                    yield MemoryWidget(classes="metric-container memory-widget", id="memory-widget")
                with Vertical():
                    yield StorageWidget(classes="metric-container storage-widget", id="storage-widget")
                    yield LogsWidget(classes="metric-container logs-widget", id="logs-widget")
            
            yield ProcessWidget(classes="metric-container process-widget", id="process-widget")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize the application."""
        self.title = "ptop - System Monitor"
        await self._start_data_collection()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_refresh(self) -> None:
        """Manually refresh all metrics."""
        self.call_from_thread(self._refresh_all_metrics)
    
    def action_help(self) -> None:
        """Show help dialog."""
        # TODO: Implement help dialog
        pass
    
    def _initialize_collectors(self) -> None:
        """Initialize all metric collectors."""
        self.collectors['cpu'] = CPUCollector()
        self.collectors['memory'] = MemoryCollector()
        self.collectors['process'] = ProcessCollector()
        self.collectors['storage'] = StorageCollector()
        self.collectors['logs'] = LogCollector()
    
    async def _start_data_collection(self) -> None:
        """Start data collection tasks for all collectors."""
        for name, collector in self.collectors.items():
            task = asyncio.create_task(self._update_collector_loop(name, collector))
            self.update_tasks[name] = task
    
    async def _update_collector_loop(self, name: str, collector: Any) -> None:
        """Continuous update loop for a collector."""
        while True:
            try:
                # Collect data
                data = await collector.collect()
                
                # Update corresponding widget
                await self._update_widget(name, data)
                
                # Wait for next update
                await asyncio.sleep(collector.update_interval)
            except Exception as e:
                # Log error but continue
                print(f"Error in {name} collector: {e}")
                await asyncio.sleep(1)
    
    async def _update_widget(self, collector_name: str, data: Dict[str, Any]) -> None:
        """Update widget with new data."""
        widget_id = f"{collector_name}-widget"
        widget = self.query_one(f"#{widget_id}", expected_type=None)
        if widget and hasattr(widget, 'update_data'):
            widget.update_data(data)
    
    async def _refresh_all_metrics(self) -> None:
        """Manually refresh all metrics."""
        for name, collector in self.collectors.items():
            try:
                data = await collector.collect()
                await self._update_widget(name, data)
            except Exception as e:
                print(f"Error refreshing {name}: {e}")