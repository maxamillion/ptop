"""Tests for base widget class."""

import pytest
from unittest.mock import MagicMock, patch
from ptop.widgets.base import BaseMetricWidget


class TestBaseMetricWidget:
    """Test BaseMetricWidget base class."""
    
    def test_initialization(self):
        """Test widget initialization."""
        widget = BaseMetricWidget()
        
        # Test initial data is empty dict
        assert widget.data == {}
        
        # Test that it inherits from Textual's Widget
        from textual.widget import Widget
        assert isinstance(widget, Widget)
    
    def test_initialization_with_kwargs(self):
        """Test widget initialization with keyword arguments."""
        # Test that kwargs are passed to parent Widget
        widget = BaseMetricWidget(id="test-widget", classes="test-class")
        
        assert widget.id == "test-widget"
        assert "test-class" in widget.classes
    
    def test_update_data(self):
        """Test data update functionality."""
        widget = BaseMetricWidget()
        
        # Mock the refresh method to track calls
        widget.refresh = MagicMock()
        
        test_data = {"cpu": 75.5, "memory": 60.2}
        widget.update_data(test_data)
        
        # Check that data was updated
        assert widget.data == test_data
        
        # Check that refresh was called (at least once due to reactive system)
        assert widget.refresh.call_count >= 1
    
    def test_update_data_multiple_times(self):
        """Test multiple data updates."""
        widget = BaseMetricWidget()
        widget.refresh = MagicMock()
        
        # First update
        data1 = {"cpu": 50.0}
        widget.update_data(data1)
        assert widget.data == data1
        
        # Second update should replace first
        data2 = {"cpu": 75.0, "memory": 80.0}
        widget.update_data(data2)
        assert widget.data == data2
        
        # Refresh should be called at least twice (may be more due to reactive system)
        assert widget.refresh.call_count >= 2
    
    def test_update_data_with_empty_dict(self):
        """Test updating with empty dictionary."""
        widget = BaseMetricWidget()
        widget.refresh = MagicMock()
        
        # Start with some data
        widget.data = {"existing": "data"}
        
        # Update with empty dict
        widget.update_data({})
        
        assert widget.data == {}
        assert widget.refresh.call_count >= 1
    
    def test_update_data_with_none_values(self):
        """Test updating with None values."""
        widget = BaseMetricWidget()
        widget.refresh = MagicMock()
        
        test_data = {"cpu": None, "memory": 50.0, "disk": None}
        widget.update_data(test_data)
        
        assert widget.data == test_data
        assert widget.data["cpu"] is None
        assert widget.data["memory"] == 50.0
        assert widget.data["disk"] is None
        assert widget.refresh.call_count >= 1
    
    def test_update_data_with_complex_data(self):
        """Test updating with complex nested data."""
        widget = BaseMetricWidget()
        widget.refresh = MagicMock()
        
        complex_data = {
            "cpu": {
                "usage": 75.5,
                "cores": [10.0, 20.0, 30.0, 40.0]
            },
            "memory": {
                "total": 16384,
                "used": 8192,
                "available": 8192
            },
            "processes": [
                {"pid": 1, "name": "init", "cpu": 0.1},
                {"pid": 2, "name": "kthreadd", "cpu": 0.0}
            ]
        }
        
        widget.update_data(complex_data)
        
        assert widget.data == complex_data
        assert widget.data["cpu"]["usage"] == 75.5
        assert len(widget.data["cpu"]["cores"]) == 4
        assert len(widget.data["processes"]) == 2
        assert widget.refresh.call_count >= 1
    
    def test_compose_method(self):
        """Test compose method returns empty generator."""
        widget = BaseMetricWidget()
        
        # compose should return a generator
        result = widget.compose()
        
        # Convert generator to list to test it
        composed_items = list(result)
        
        # Should be empty by default
        assert composed_items == []
    
    def test_reactive_data_property(self):
        """Test that data is a reactive property."""
        widget = BaseMetricWidget()
        
        # Check that reactive descriptor exists
        assert hasattr(BaseMetricWidget, 'data')
        
        # Test that data changes are tracked (basic check)
        widget.data = {"test": "value"}
        assert widget.data == {"test": "value"}
    
    def test_data_isolation_between_instances(self):
        """Test that data is isolated between widget instances."""
        widget1 = BaseMetricWidget()
        widget2 = BaseMetricWidget()
        
        # Both should start with empty data
        assert widget1.data == {}
        assert widget2.data == {}
        
        # Update one widget
        widget1.update_data({"widget1": "data"})
        
        # Other widget should be unaffected
        assert widget1.data == {"widget1": "data"}
        assert widget2.data == {}
        
        # Update second widget
        widget2.update_data({"widget2": "data"})
        
        # Both should have their own data
        assert widget1.data == {"widget1": "data"}
        assert widget2.data == {"widget2": "data"}
    
    def test_inheritance_and_override(self):
        """Test that BaseMetricWidget can be properly inherited and overridden."""
        
        class TestWidget(BaseMetricWidget):
            def compose(self):
                yield from ["test_component"]
            
            def custom_method(self):
                return "custom"
        
        widget = TestWidget()
        
        # Test that base functionality still works
        widget.update_data({"test": "data"})
        assert widget.data == {"test": "data"}
        
        # Test that compose was overridden
        composed = list(widget.compose())
        assert composed == ["test_component"]
        
        # Test custom method
        assert widget.custom_method() == "custom"
    
    def test_widget_lifecycle_methods(self):
        """Test interaction with Textual widget lifecycle."""
        widget = BaseMetricWidget()
        
        # Test that basic Widget methods are available
        assert hasattr(widget, 'mount')
        assert hasattr(widget, 'refresh')
        assert hasattr(widget, 'remove')
        
        # Test that methods can be called without error
        # (Note: In a real Textual app, these would have more complex behavior)
        widget.refresh()  # Should not raise an error