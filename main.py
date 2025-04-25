import json
import os
import logging
import requests
import argparse
import sys
from pathlib import Path
from typing import Set, Dict, Any, List, Tuple
from apscheduler.schedulers.background import BackgroundScheduler
from time import sleep
from xml.etree import ElementTree as ET
from notifications import NotifiarrService
from configurations.torznab_config import TorznabConfiguration, TorznabEndpoint
from configurations.notification_config import NotificationConfig

# Create module-level logger
logger = logging.getLogger(__name__)

def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger.setLevel(level)

class TorznabMonitor:
    def __init__(self, config_path: str = "config.json", mapping_path: str = "notification_mapping.json", skip_init: bool = False):
        # Check for required config files
        config_file = Path(config_path)
        mapping_file = Path(mapping_path)
        
        if not config_file.exists():
            logger.error(f"Configuration file not found in {config_path}")
            logger.error("Please ensure the file exists at the specified path")
            sys.exit(1)
            
        if not mapping_file.exists():
            logger.error(f"Notification mapping file not found in {mapping_path}")
            logger.error("Please ensure the file exists at the specified path")
            sys.exit(1)
            
        self.config = self._load_config(str(config_file))
        self.torznab_config = TorznabConfiguration.from_file(str(config_file))
        if not self.torznab_config.validate():
            raise ValueError("Invalid Torznab configuration")
            
        self._ensure_data_directory()
        self.scheduler = BackgroundScheduler()
        self.notification_service = NotifiarrService(
            api_key=self.config["notifiarr"]["api_key"],
            channel_id=self.config["notifiarr"]["discord"]["channel_id"],
            webhook_url=self.config["notifiarr"]["url"]
        )
        self.notification_config = NotificationConfig(str(mapping_file))
        self.skip_init = skip_init
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file: {config_path}")
            raise

    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        data_dir = Path("/data")
        data_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_seen_file_path(self, mapping_name: str) -> Path:
        """Get the path to the seen file for a specific mapping."""
        return Path("/data") / f"seen_{mapping_name}.json"
        
    def _load_seen(self, mapping_name: str) -> Set[str]:
        """Load seen entries from file for a specific mapping."""
        seen_file = self._get_seen_file_path(mapping_name)
        try:
            with open(seen_file, 'r') as f:
                # Clean each GUID when loading
                return {self._clean_guid(guid) for guid in json.load(f)}
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Could not load seen entries for {mapping_name}, starting with empty set")
            return set()

    def _save_seen(self, seen: Set[str], mapping_name: str) -> None:
        """Save seen entries to file for a specific mapping."""
        seen_file = self._get_seen_file_path(mapping_name)
        try:
            # Convert set to list and limit to 200 items
            seen_list = list(seen)
            if len(seen_list) > 200:
                seen_list = seen_list[-200:]  # Keep only the last 200 items
                logger.debug(f"Seen items limit reached for {mapping_name}, keeping only the last 200 items")
            
            with open(seen_file, 'w') as f:
                json.dump(seen_list, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save seen entries for {mapping_name}: {e}")

    def _clear_seen(self, mapping_name: str) -> None:
        """Clear the seen items file for a specific mapping."""
        seen_file = self._get_seen_file_path(mapping_name)
        if seen_file.exists():
            logger.info(f"Clearing existing seen items file for {mapping_name}")
            seen_file.unlink()

    def _clean_guid(self, guid: str) -> str:
        """
        Clean the GUID URL by keeping only the id parameter.
        
        Args:
            guid: The GUID URL to clean
            
        Returns:
            Cleaned GUID URL with only id parameter
        """
        try:
            # Split on '?' to separate base URL and parameters
            base_url, params = guid.split('?', 1)
            # Find the id parameter
            for param in params.split('&'):
                if param.startswith('id='):
                    return f"{base_url}?{param}"
            return base_url
        except Exception as e:
            logger.error(f"Failed to clean GUID: {e}")
            return guid

    def _extract_torznab_attr(self, item: ET.Element, attr_name: str) -> Set[str]:
        """
        Extract all values of a given torznab:attr name from an XML item.
        """
        values = set()
        try:
            for attr in item.findall(f".//{{*}}attr[@name='{attr_name}']"):
                values.add(attr.attrib.get("value"))
        except Exception as e:
            logger.error(f"Failed to extract torznab attribute '{attr_name}': {e}")
        return values

    def _extract_categories(self, item: ET.Element) -> Set[str]:
        """Extract categories from Torznab item."""
        return self._extract_torznab_attr(item, 'category')

    def _send_notification(self, item: ET.Element, endpoint: TorznabEndpoint) -> None:
        """
        Send notification for new item.
        
        Args:
            item: The XML item element
            endpoint: The Torznab endpoint
        """
        try:
            mapping_name = f"{endpoint.name}-notifiarr"
            notification_data = self.notification_config.get_notification_data(item, mapping_name)
            self.notification_service.send_notification(**notification_data)
        except KeyError as e:
            logger.error(f"Notification mapping not found: {e}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)

    def _fetch_torznab_feed(self, endpoint: TorznabEndpoint) -> Tuple[ET.Element, List[ET.Element]]:
        """
        Fetch and parse the Torznab feed for a given endpoint.
        
        Args:
            endpoint: The Torznab endpoint to fetch from
            
        Returns:
            Tuple containing the root element and list of item elements.
            
        Raises:
            requests.RequestException: If the request fails.
            ET.ParseError: If the XML parsing fails.
        """
        response = requests.get(endpoint.url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        # Log feed details
        logger.info(f"Feed version: {root.tag}")
        items = root.findall('.//item')
        logger.info(f"Number of entries: {len(items)}")
        
        # Log first item details for debugging
        if items:
            first_item = items[0]
            logger.debug("First item details:")
            logger.debug(f"Title: {first_item.find('title').text if first_item.find('title') is not None else 'No title'}")
            logger.debug(f"Link: {first_item.find('link').text if first_item.find('link') is not None else 'No link'}")
            logger.debug(f"Categories: {list(self._extract_categories(first_item))}")
            
        return root, items

    def _process_items(self, items: List[ET.Element], categories: Set[str], mapping_name: str) -> List[ET.Element]:
        """
        Process a list of Torznab items, filtering by category and tracking seen items.
        Seen items are saved immediately after processing.
        
        Args:
            items: List of XML item elements to process
            categories: Set of categories to filter by
            mapping_name: Name of the mapping for seen items tracking
            
        Returns:
            List of matching items that need notifications
        """
        seen = self._load_seen(mapping_name)
        matching_items = []
        
        for item in items:
            guid = item.find('guid').text if item.find('guid') is not None else None
            title = item.find('title').text if item.find('title') is not None else "No title"
            
            if not guid:
                logger.debug(f"Skipping item '{title}' - no GUID")
                continue

            # Clean the GUID before checking
            cleaned_guid = self._clean_guid(guid)
            if cleaned_guid in seen:
                logger.debug(f"Skipping item '{title}' - already seen")
                continue

            item_categories = self._extract_categories(item)
            if categories & item_categories:
                logger.info(f"Found matching categories for item '{title}'")
                matching_items.append(item)
                seen.add(cleaned_guid)
            else:
                logger.debug(f"No matching categories for item '{title}'")
        
        # Save seen items after processing
        self._save_seen(seen, mapping_name)
        return matching_items

    def poll_torznab(self, endpoint: TorznabEndpoint) -> None:
        """
        Poll Torznab feed for new entries.
        
        Args:
            endpoint: The Torznab endpoint to poll.
        """
        logger.info(f"Polling Torznab feed for endpoint: {endpoint.url}")
        mapping_name = f"{endpoint.name}-notifiarr"
        
        try:
            _, items = self._fetch_torznab_feed(endpoint)
            
            # Process items in reverse order to maintain FIFO
            matching_items = self._process_items(reversed(items), endpoint.categories, mapping_name)
            
            # Send notifications for matching items
            for item in matching_items:
                self._send_notification(item, endpoint)
            
            logger.info(f"Processed feed for {mapping_name}")
        except Exception as e:
            logger.error(f"Error polling Torznab feed: {e}", exc_info=True)

    def _initialize_seen_items(self, endpoint: TorznabEndpoint) -> None:
        """
        Initialize seen items with current feed items without sending notifications.
        Only items matching the configured categories will be marked as seen.
        Existing seen items will be cleared before initialization.
        
        Args:
            endpoint: The Torznab endpoint to initialize seen items for.
        """
        logger.info(f"Initializing seen items from current feed for endpoint: {endpoint.url}")
        try:
            mapping_name = f"{endpoint.name}-notifiarr"
            
            # Clear existing seen items file
            self._clear_seen(mapping_name)

            _, items = self._fetch_torznab_feed(endpoint)
            
            # Process items without sending notifications
            matching_items = self._process_items(items, endpoint.categories, mapping_name)
            
            logger.info(f"Initialized seen items for {mapping_name}: {len(matching_items)} items")
        except Exception as e:
            logger.error(f"Failed to initialize seen items: {e}", exc_info=True)

    def start(self) -> None:
        """Start the Torznab monitor."""
        endpoint = self.torznab_config.get_first_endpoint()
        
        # Initialize seen items first if not skipped
        if not self.skip_init:
            self._initialize_seen_items(endpoint)
        else:
            logger.info("Skipping seen items initialization")
        
        # Start the scheduler
        self.scheduler.add_job(
            self.poll_torznab,
            "interval",
            seconds=endpoint.poll_interval,
            args=[endpoint]  # Pass the endpoint to the job
        )
        self.scheduler.start()
        logger.info("Torznab Monitor started. Press Ctrl+C to exit.")

    def stop(self) -> None:
        """Stop the Torznab monitor."""
        self.scheduler.shutdown()
        logger.info("Torznab Monitor stopped.")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Torznab Monitor')
    parser.add_argument(
        '--skip-init',
        action='store_true',
        help='Skip initializing seen items'
    )
    parser.add_argument(
        '--config',
        default='config/config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--mapping',
        default='config/notification_mapping.json',
        help='Path to notification mapping file (default: notification_mapping.json)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()

def main():
    """Main function to run the application."""
    args = parse_args()
    setup_logging(debug=args.debug)
    monitor = TorznabMonitor(
        config_path=args.config,
        mapping_path=args.mapping,
        skip_init=args.skip_init
    )
    try:
        monitor.start()
        while True:
            sleep(1)
    except KeyboardInterrupt:
        monitor.stop()

if __name__ == "__main__":
    main()
