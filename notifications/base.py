from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class NotificationService(ABC):
    """Base class for notification services."""
    
    @abstractmethod
    def send_notification(self, title: str, message: str, link: str = "", description: str = "") -> bool:
        """
        Send a notification.
        
        Args:
            title: The notification title
            message: The notification message
            link: Optional link to include
            description: Optional description
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        pass 