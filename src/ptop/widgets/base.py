"""Base widget classes for ptop UI components."""

from textual.widget import Widget
from textual.reactive import reactive
from typing import Dict, Any


class BaseMetricWidget(Widget):
    """Base class for all metric display widgets."""
    
    data = reactive({})
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data = {}
    
    def update_data(self, new_data: Dict[str, Any]) -> None:
        """Update widget data and trigger re-render.
        
        Args:
            new_data: New data to display.
        """
        self.data = new_data
        self.refresh()
    
    def compose(self):
        """Compose the widget layout. Override in subclasses."""
        yield from []