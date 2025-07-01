"""Configuration management for ptop."""

from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path


class PtopSettings(BaseModel):
    """Main configuration class for ptop."""
    
    # Update intervals (seconds)
    cpu_update_interval: float = 1.0
    memory_update_interval: float = 1.0
    storage_update_interval: float = 2.0
    process_update_interval: float = 2.0
    log_update_interval: float = 5.0
    
    # Display settings
    show_cpu_per_core: bool = True
    show_memory_swap: bool = True
    show_process_tree: bool = False
    process_count_limit: int = 50
    
    # Thresholds for alerts
    cpu_warning_threshold: float = 70.0
    cpu_critical_threshold: float = 90.0
    memory_warning_threshold: float = 80.0
    memory_critical_threshold: float = 95.0
    
    # Log monitoring
    log_sources: list[str] = ["/var/log/messages", "/var/log/syslog"]
    error_patterns: list[str] = ["error", "critical", "fatal", "panic"]
    
    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "PtopSettings":
        """Load settings from configuration file.
        
        Args:
            config_path: Path to config file. If None, uses default locations.
            
        Returns:
            PtopSettings instance.
        """
        if config_path is None:
            # Try default locations
            config_dirs = [
                Path.home() / ".config" / "ptop",
                Path("/etc/ptop"),
                Path.cwd()
            ]
            
            for config_dir in config_dirs:
                potential_path = config_dir / "config.json"
                if potential_path.exists():
                    config_path = potential_path
                    break
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls(**config_data)
        
        return cls()
    
    def save_to_file(self, config_path: Path) -> None:
        """Save settings to configuration file.
        
        Args:
            config_path: Path where to save the config.
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)