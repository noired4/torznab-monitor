from dataclasses import dataclass
from typing import Dict, Any, Optional
from xml.etree import ElementTree as ET
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class NotificationMapping:
    """Configuration for notification field mappings."""
    type: str  # 'xml_tag', 'torznab_attr', or 'static'
    path: Optional[str] = None  # For xml_tag
    name: Optional[str] = None  # For torznab_attr
    value: Optional[str] = None  # For static
    select: Optional[str] = None  # For torznab_attr: 'first' or 'all'

    @classmethod
    def from_dict(cls, mapping_dict: dict) -> 'NotificationMapping':
        """Create a NotificationMapping instance from a dictionary."""
        return cls(
            type=mapping_dict['type'],
            path=mapping_dict.get('path'),
            name=mapping_dict.get('name'),
            value=mapping_dict.get('value'),
            select=mapping_dict.get('select')
        )

class NotificationConfig:
    """Configuration class for notification settings."""
    
    def __init__(self, config_path: str = "notification_mapping.json"):
        self.mappings = self._load_mappings(config_path)
        
    def _load_mappings(self, config_path: str) -> Dict[str, Dict[str, NotificationMapping]]:
        """Load notification mappings from file."""
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
                return {
                    mapping_name: {
                        field: NotificationMapping.from_dict(field_mapping)
                        for field, field_mapping in mapping_config.items()
                    }
                    for mapping_name, mapping_config in config_dict.get('mappings', {}).items()
                }
        except FileNotFoundError:
            logger.error(f"Notification mapping file not found: {config_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in notification mapping file: {config_path}")
            raise
            
    def _extract_torznab_attr(self, item: ET.Element, attr_name: str, select: str = 'first') -> Any:
        """
        Extract values of a given torznab:attr name from an XML item.
        
        Args:
            item: The XML item element
            attr_name: The name of the torznab attribute to extract
            select: How to select the value ('first' or 'all')
            
        Returns:
            The selected value(s) from the attribute
        """
        values = []
        try:
            for attr in item.findall(f".//{{*}}attr[@name='{attr_name}']"):
                values.append(attr.attrib.get("value"))
        except Exception as e:
            logger.error(f"Failed to extract torznab attribute '{attr_name}': {e}")
            
        if not values:
            return None
            
        return values[0] if select == 'first' else values
        
    def _extract_xml_tag(self, item: ET.Element, path: str) -> Optional[str]:
        """
        Extract value from an XML tag.
        
        Args:
            item: The XML item element
            path: The path to the tag
            
        Returns:
            The text content of the tag if found, None otherwise
        """
        try:
            element = item.find(path)
            return element.text if element is not None else None
        except Exception as e:
            logger.error(f"Failed to extract XML tag '{path}': {e}")
            return None
            
    def get_notification_data(self, item: ET.Element, mapping_name: str) -> Dict[str, Any]:
        """
        Get notification data for an item based on the mapping configuration.
        
        Args:
            item: The XML item element to extract data from
            mapping_name: The name of the mapping to use (e.g., 'fdc-notifiarr')
            
        Returns:
            Dictionary of notification field values
            
        Raises:
            KeyError: If the specified mapping name doesn't exist
        """
        if mapping_name not in self.mappings:
            raise KeyError(f"Notification mapping '{mapping_name}' not found")
            
        mapping = self.mappings[mapping_name]
        data = {}
        
        for field, field_mapping in mapping.items():
            try:
                if field_mapping.type == 'static':
                    data[field] = field_mapping.value
                elif field_mapping.type == 'xml_tag':
                    data[field] = self._extract_xml_tag(item, field_mapping.path)
                elif field_mapping.type == 'torznab_attr':
                    data[field] = self._extract_torznab_attr(item, field_mapping.name, field_mapping.select)
            except Exception as e:
                logger.error(f"Failed to extract field '{field}': {e}")
                data[field] = None
                
        return data 