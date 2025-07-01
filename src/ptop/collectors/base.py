"""Base collector class for system metrics."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseCollector(ABC):
    """Abstract base class for all system metric collectors."""

    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """Collect system metrics and return as dictionary.
        
        Returns:
            Dict containing collected metrics data.
        """
        pass

    @property
    @abstractmethod
    def update_interval(self) -> float:
        """Get the recommended update interval in seconds.
        
        Returns:
            Update interval in seconds.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the collector name.
        
        Returns:
            Collector name.
        """
        pass