from dataclasses import dataclass
from typing import Set, Dict
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class TorznabEndpoint:
    """Configuration for a single Torznab endpoint."""
    name: str
    url: str
    categories: Set[str]
    poll_interval: int

    @classmethod
    def from_dict(cls, endpoint_dict: dict, endpoint_name: str) -> 'TorznabEndpoint':
        """
        Create a TorznabEndpoint instance from a dictionary.
        
        Args:
            endpoint_dict: Dictionary containing endpoint configuration
            endpoint_name: Name of the endpoint (key from config)
        """
        try:
            return cls(
                name=endpoint_name,
                url=endpoint_dict.get('url', ''),
                categories=set(endpoint_dict.get('categories', [])),
                poll_interval=endpoint_dict.get('poll_interval', 1800)
            )
        except Exception as e:
            logger.error(f"Failed to create TorznabEndpoint: {e}")
            raise

    def validate(self) -> bool:
        """Validate the endpoint configuration values."""
        if not self.name:
            logger.error("Endpoint name is not set")
            return False
            
        if not self.url:
            logger.error("Torznab URL is not set")
            return False
        
        if not self.categories:
            logger.error("No categories specified")
            return False
        
        if self.poll_interval < 60:
            logger.warning("Poll interval is less than 60 seconds, this might be too aggressive")
        
        return True

@dataclass
class TorznabConfiguration:
    """Configuration class for Torznab settings."""
    endpoints: Dict[str, TorznabEndpoint]

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'TorznabConfiguration':
        """Create a TorznabConfiguration instance from a dictionary."""
        try:
            torznab_config = config_dict.get('torznab', {})
            endpoints = {}
            for endpoint_name, endpoint_config in torznab_config.get('endpoints', {}).items():
                endpoints[endpoint_name] = TorznabEndpoint.from_dict(endpoint_config, endpoint_name)
            return cls(endpoints=endpoints)
        except Exception as e:
            logger.error(f"Failed to create TorznabConfiguration: {e}")
            raise

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> 'TorznabConfiguration':
        """Create a TorznabConfiguration instance from a configuration file."""
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
                return cls.from_dict(config_dict)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file: {config_path}")
            raise

    def validate(self) -> bool:
        """Validate the configuration values."""
        if not self.endpoints:
            logger.error("No Torznab endpoints configured")
            return False
        
        for endpoint_name, endpoint in self.endpoints.items():
            if not endpoint.validate():
                logger.error(f"Invalid configuration for endpoint: {endpoint_name}")
                return False
        
        return True

    def get_first_endpoint(self) -> TorznabEndpoint:
        """Get the first configured endpoint."""
        if not self.endpoints:
            raise ValueError("No Torznab endpoints configured")
        return next(iter(self.endpoints.values())) 