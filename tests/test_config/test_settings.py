"""Tests for configuration system."""

import pytest
from unittest.mock import patch, mock_open
import json
import tempfile
from pathlib import Path
from ptop.config.settings import PtopSettings


class TestPtopSettingsDefaults:
    """Test default settings values."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = PtopSettings()
        
        # Update intervals
        assert settings.cpu_update_interval == 1.0
        assert settings.memory_update_interval == 1.0
        assert settings.storage_update_interval == 2.0
        assert settings.process_update_interval == 2.0
        assert settings.log_update_interval == 5.0
        
        # Display settings
        assert settings.show_cpu_per_core is True
        assert settings.show_memory_swap is True
        assert settings.show_process_tree is False
        assert settings.process_count_limit == 50
        
        # Thresholds
        assert settings.cpu_warning_threshold == 70.0
        assert settings.cpu_critical_threshold == 90.0
        assert settings.memory_warning_threshold == 80.0
        assert settings.memory_critical_threshold == 95.0
        
        # Log monitoring
        assert settings.log_sources == ["/var/log/messages", "/var/log/syslog"]
        assert settings.error_patterns == ["error", "critical", "fatal", "panic"]
    
    def test_custom_values_initialization(self):
        """Test initialization with custom values."""
        custom_settings = PtopSettings(
            cpu_update_interval=2.5,
            show_cpu_per_core=False,
            cpu_warning_threshold=85.0,
            log_sources=["/custom/log/path"],
            error_patterns=["custom_error"]
        )
        
        assert custom_settings.cpu_update_interval == 2.5
        assert custom_settings.show_cpu_per_core is False
        assert custom_settings.cpu_warning_threshold == 85.0
        assert custom_settings.log_sources == ["/custom/log/path"]
        assert custom_settings.error_patterns == ["custom_error"]
        
        # Check that other defaults are preserved
        assert custom_settings.memory_update_interval == 1.0
        assert custom_settings.process_count_limit == 50


class TestPtopSettingsFileOperations:
    """Test file loading and saving operations."""
    
    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file returns defaults."""
        with patch('pathlib.Path.exists', return_value=False):
            settings = PtopSettings.load_from_file(Path("/nonexistent/config.json"))
            assert settings.cpu_update_interval == 1.0
            assert settings.show_cpu_per_core is True
    
    def test_load_from_specific_file(self):
        """Test loading from a specific config file."""
        config_data = {
            "cpu_update_interval": 2.5,
            "show_cpu_per_core": False,
            "cpu_warning_threshold": 85.0,
            "log_sources": ["/custom/log"]
        }
        
        mock_file_content = json.dumps(config_data)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            
            settings = PtopSettings.load_from_file(Path("/test/config.json"))
            
            assert settings.cpu_update_interval == 2.5
            assert settings.show_cpu_per_core is False
            assert settings.cpu_warning_threshold == 85.0
            assert settings.log_sources == ["/custom/log"]
            # Check that unspecified values use defaults
            assert settings.memory_update_interval == 1.0
    
    def test_load_from_default_locations(self):
        """Test loading from default config locations."""
        config_data = {"cpu_update_interval": 3.0}
        mock_file_content = json.dumps(config_data)
        
        # Mock the second default location to exist
        def mock_exists(self):
            return str(self) == "/etc/ptop/config.json"
        
        with patch.object(Path, 'exists', mock_exists), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            
            settings = PtopSettings.load_from_file()
            assert settings.cpu_update_interval == 3.0
    
    def test_load_from_home_config(self):
        """Test loading from home directory config."""
        config_data = {"memory_update_interval": 1.5}
        mock_file_content = json.dumps(config_data)
        
        # Mock the first default location (home) to exist
        def mock_exists(self):
            return ".config/ptop/config.json" in str(self)
        
        with patch.object(Path, 'exists', mock_exists), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            
            settings = PtopSettings.load_from_file()
            assert settings.memory_update_interval == 1.5
    
    def test_save_to_file(self):
        """Test saving settings to file."""
        settings = PtopSettings(cpu_update_interval=2.0, show_cpu_per_core=False)
        
        mock_file = mock_open()
        test_path = Path("/test/config.json")
        
        with patch('builtins.open', mock_file), \
             patch.object(Path, 'mkdir'):
            
            settings.save_to_file(test_path)
            
            # Verify file was opened for writing
            mock_file.assert_called_once_with(test_path, 'w')
            
            # Get the written content
            written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
            saved_data = json.loads(written_content)
            
            assert saved_data["cpu_update_interval"] == 2.0
            assert saved_data["show_cpu_per_core"] is False
            assert "memory_update_interval" in saved_data  # All fields should be saved
    
    def test_save_creates_parent_directory(self):
        """Test that save_to_file creates parent directories."""
        settings = PtopSettings()
        test_path = Path("/test/subdir/config.json")
        
        with patch('builtins.open', mock_open()), \
             patch.object(Path, 'mkdir') as mock_mkdir:
            
            settings.save_to_file(test_path)
            
            # Verify mkdir was called with correct arguments
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestPtopSettingsValidation:
    """Test settings validation and edge cases."""
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in config file."""
        invalid_json = "{ invalid json content"
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=invalid_json)), \
             pytest.raises(json.JSONDecodeError):
            
            PtopSettings.load_from_file(Path("/test/invalid.json"))
    
    def test_partial_config_file(self):
        """Test loading config with only some fields specified."""
        partial_config = {
            "cpu_update_interval": 0.5,
            "log_sources": ["/var/log/custom"]
        }
        mock_content = json.dumps(partial_config)
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_content)):
            
            settings = PtopSettings.load_from_file(Path("/test/partial.json"))
            
            # Check specified values
            assert settings.cpu_update_interval == 0.5
            assert settings.log_sources == ["/var/log/custom"]
            
            # Check defaults for unspecified values
            assert settings.memory_update_interval == 1.0
            assert settings.show_cpu_per_core is True
            assert settings.error_patterns == ["error", "critical", "fatal", "panic"]
    
    def test_type_validation(self):
        """Test that pydantic validates types correctly."""
        # This should work
        settings = PtopSettings(cpu_update_interval=1.5)
        assert settings.cpu_update_interval == 1.5
        
        # This should also work (int to float conversion)
        settings = PtopSettings(cpu_update_interval=2)
        assert settings.cpu_update_interval == 2.0
        
        # Test boolean conversion
        settings = PtopSettings(show_cpu_per_core=1)
        assert settings.show_cpu_per_core is True
    
    def test_model_dump(self):
        """Test that model_dump returns all fields."""
        settings = PtopSettings(cpu_update_interval=1.5)
        data = settings.model_dump()
        
        expected_keys = {
            'cpu_update_interval', 'memory_update_interval', 'storage_update_interval',
            'process_update_interval', 'log_update_interval', 'show_cpu_per_core',
            'show_memory_swap', 'show_process_tree', 'process_count_limit',
            'cpu_warning_threshold', 'cpu_critical_threshold', 'memory_warning_threshold',
            'memory_critical_threshold', 'log_sources', 'error_patterns'
        }
        
        assert set(data.keys()) == expected_keys
        assert data['cpu_update_interval'] == 1.5


class TestPtopSettingsEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_config_file(self):
        """Test loading from empty config file."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="{}")):
            
            settings = PtopSettings.load_from_file(Path("/test/empty.json"))
            # Should use all defaults
            assert settings.cpu_update_interval == 1.0
            assert settings.show_cpu_per_core is True
    
    def test_file_permission_error_on_save(self):
        """Test handling of permission errors when saving."""
        settings = PtopSettings()
        test_path = Path("/root/config.json")
        
        with patch('builtins.open', side_effect=PermissionError("Access denied")), \
             patch.object(Path, 'mkdir'), \
             pytest.raises(PermissionError):
            
            settings.save_to_file(test_path)
    
    def test_file_not_found_error_on_load(self):
        """Test handling when config file exists but can't be read."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=FileNotFoundError("File not found")), \
             pytest.raises(FileNotFoundError):
            
            PtopSettings.load_from_file(Path("/test/missing.json"))
    
    def test_all_default_locations_missing(self):
        """Test when no default config locations exist."""
        with patch('pathlib.Path.exists', return_value=False):
            settings = PtopSettings.load_from_file()
            # Should return default settings
            assert settings.cpu_update_interval == 1.0
            assert settings.show_cpu_per_core is True