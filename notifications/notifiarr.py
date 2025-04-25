import requests
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader
from .base import NotificationService

logger = logging.getLogger(__name__)

class NotifiarrService(NotificationService):
    """Notifiarr notification service implementation."""
    
    def __init__(self, api_key: str, channel_id: int, webhook_url: str = "https://notifiarr.com/api/v1/notification/passthrough"):
        """
        Initialize Notifiarr service.
        
        Args:
            api_key: Notifiarr API key
            channel_id: Discord channel ID to send notifications to
            webhook_url: Notifiarr webhook URL
        """
        self.api_key = api_key
        self.channel_id = channel_id
        self.webhook_url = f"{webhook_url}/{api_key}"
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template('notifiarr.json.j2')
        
    def send_notification(
        self,
        title: str,
        name: str = "",
        event: str = "",
        content: str = "",
        description: str = "",
        color: str = "00FF00",
        ping_user: Optional[int] = None,
        ping_role: Optional[int] = None,
        thumbnail: str = "",
        image: str = "",
        icon: str = "",
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: str = ""
    ) -> bool:
        """
        Send a notification via Notifiarr.
        
        Args:
            title: The notification title
            name: The notification name
            event: The notification event
            description: Optional description
            color: Optional color code (6 digit HTML color)
            ping_user: Optional Discord user ID to ping
            ping_role: Optional Discord role ID to ping
            thumbnail: Optional thumbnail URL
            image: Optional image URL
            icon: Optional icon URL
            fields: Optional list of fields to include
            footer: Optional footer text
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        # Prepare template variables
        template_vars = {
            "channel_id": self.channel_id,
            "title": title,
            "name": name,
            "event": event,
            "description": description,
            "content": content,
            "color": color,
            "ping_user": ping_user,
            "ping_role": ping_role,
            "thumbnail": thumbnail,
            "image": image,
            "icon": icon,
            "fields": fields,
            "footer": footer
        }
        
        # Render template and send notification
        try:
            payload = self.template.render(**template_vars)
            logger.debug(f"Notification payload: {payload}")
            
            # Send notification
            response = requests.post(self.webhook_url, json=json.loads(payload))
            response.raise_for_status()
            logger.info(f"Sent notification: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False 