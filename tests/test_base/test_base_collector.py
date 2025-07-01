"""Tests for base collector class."""

import pytest
from abc import ABC
from ptop.collectors.base import BaseCollector


class TestBaseCollector:
    """Test BaseCollector abstract base class."""
    
    def test_is_abstract_class(self):
        """Test that BaseCollector is an abstract class."""
        assert issubclass(BaseCollector, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseCollector()
    
    def test_abstract_methods_defined(self):
        """Test that abstract methods are properly defined."""
        # Check that abstract methods exist
        assert hasattr(BaseCollector, 'collect')
        assert hasattr(BaseCollector, 'update_interval')
        assert hasattr(BaseCollector, 'name')
        
        # Check that they are marked as abstract
        assert BaseCollector.collect.__isabstractmethod__
        assert BaseCollector.update_interval.__isabstractmethod__
        assert BaseCollector.name.__isabstractmethod__
    
    def test_concrete_implementation_works(self):
        """Test that concrete implementations work correctly."""
        
        class TestCollector(BaseCollector):
            async def collect(self):
                return {"test": "data"}
            
            @property
            def update_interval(self):
                return 1.0
            
            @property
            def name(self):
                return "test_collector"
        
        # Should be able to instantiate concrete implementation
        collector = TestCollector()
        assert collector.name == "test_collector"
        assert collector.update_interval == 1.0
    
    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementations fail to instantiate."""
        
        class IncompleteCollector(BaseCollector):
            # Missing collect method
            @property
            def update_interval(self):
                return 1.0
            
            @property
            def name(self):
                return "incomplete"
        
        with pytest.raises(TypeError):
            IncompleteCollector()
    
    def test_missing_property_fails(self):
        """Test that missing property implementations fail."""
        
        class MissingPropertyCollector(BaseCollector):
            async def collect(self):
                return {}
            
            # Missing update_interval and name properties
        
        with pytest.raises(TypeError):
            MissingPropertyCollector()
    
    @pytest.mark.asyncio
    async def test_collect_method_signature(self):
        """Test collect method signature and return type."""
        
        class TestCollector(BaseCollector):
            async def collect(self):
                return {"cpu": 50.0, "memory": 60.0}
            
            @property
            def update_interval(self):
                return 2.0
            
            @property
            def name(self):
                return "test"
        
        collector = TestCollector()
        result = await collector.collect()
        
        assert isinstance(result, dict)
        assert "cpu" in result
        assert "memory" in result
        assert result["cpu"] == 50.0
        assert result["memory"] == 60.0
    
    def test_property_types(self):
        """Test that properties return correct types."""
        
        class TypeTestCollector(BaseCollector):
            async def collect(self):
                return {}
            
            @property
            def update_interval(self):
                return 1.5
            
            @property
            def name(self):
                return "type_test"
        
        collector = TypeTestCollector()
        
        # Test update_interval returns float
        assert isinstance(collector.update_interval, (int, float))
        assert collector.update_interval == 1.5
        
        # Test name returns string
        assert isinstance(collector.name, str)
        assert collector.name == "type_test"
    
    def test_inheritance_chain(self):
        """Test inheritance chain and method resolution."""
        
        class BaseTestCollector(BaseCollector):
            async def collect(self):
                return {"base": True}
            
            @property
            def update_interval(self):
                return 1.0
            
            @property
            def name(self):
                return "base_test"
        
        class DerivedTestCollector(BaseTestCollector):
            async def collect(self):
                base_data = await super().collect()
                base_data.update({"derived": True})
                return base_data
            
            @property
            def name(self):
                return "derived_test"
        
        derived = DerivedTestCollector()
        assert derived.name == "derived_test"
        assert derived.update_interval == 1.0  # Inherited from base
        
        # Test that collect method is properly overridden
        import asyncio
        result = asyncio.run(derived.collect())
        assert result == {"base": True, "derived": True}