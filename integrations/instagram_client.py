import requests
from config import Config
from typing import Optional, Dict, List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class InstagramClient:
    def __init__(self):
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.page_id = Config.INSTAGRAM_PAGE_ID
        self.base_url = "https://graph.facebook.com/v23.0"
        self.verify_token = getattr(Config, 'INSTAGRAM_VERIFY_TOKEN', None)
        
        # Rate limiting and retry settings
        self.max_retries = 3
        self.timeout = 30
        
        logger.info("InstagramClient initialized successfully")
    
    def send_message(self, recipient_id: str, message_text: str, quick_replies: Optional[List[Dict]] = None) -> bool:
        """
        Send message to Instagram user via Graph API
        
        Args:
            recipient_id: Instagram user ID to send message to
            message_text: Text message to send
            quick_replies: Optional list of quick reply options
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not recipient_id or not message_text:
            logger.error("Missing recipient_id or message_text")
            return False
            
        url = f"{self.base_url}/{self.page_id}/messages"
        
        # Build message payload
        message_payload = {"text": message_text}
        
        # Add quick replies if provided
        if quick_replies:
            message_payload["quick_replies"] = quick_replies
        
        payload = {
            "recipient": {"id": recipient_id},
            "message": message_payload,
            "messaging_type": "RESPONSE"
        }
        
        params = {
            "access_token": self.access_token
        }
        
        # Retry logic for reliability
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url, 
                    json=payload, 
                    params=params, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                logger.info(f"Message sent successfully to {recipient_id} (attempt {attempt + 1})")
                return True
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for sending message to {recipient_id}: {e}")
                
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"Instagram API Error: {error_data}")
                    except:
                        logger.error(f"Response content: {e.response.text}")
                
                # Don't retry on client errors (4xx)
                if hasattr(e, 'response') and e.response is not None:
                    if 400 <= e.response.status_code < 500:
                        logger.error(f"Client error {e.response.status_code}, not retrying")
                        break
                
                if attempt == self.max_retries - 1:
                    logger.error(f"All {self.max_retries} attempts failed for {recipient_id}")
        
        return False
    
    def send_typing_action(self, recipient_id: str) -> bool:
        """Send typing indicator to user"""
        url = f"{self.base_url}/{self.page_id}/messages"
        
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": "typing_on"
        }
        
        params = {
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, json=payload, params=params, timeout=self.timeout)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.warning(f"Failed to send typing action: {e}")
            return False
    
    def send_quick_replies(self, recipient_id: str, message_text: str, quick_replies: List[str]) -> bool:
        """
        Send message with quick reply buttons
        
        Args:
            recipient_id: Instagram user ID
            message_text: Main message text
            quick_replies: List of quick reply options (max 13)
            
        Returns:
            bool: Success status
        """
        if not quick_replies or len(quick_replies) > 13:
            logger.error("Quick replies must be between 1-13 options")
            return False
        
        # Format quick replies for Instagram API
        formatted_replies = []
        for i, reply in enumerate(quick_replies[:13]):  # Limit to 13
            formatted_replies.append({
                "content_type": "text",
                "title": reply[:20],  # Max 20 characters
                "payload": f"QUICK_REPLY_{i}_{reply.upper().replace(' ', '_')}"
            })
        
        return self.send_message(recipient_id, message_text, formatted_replies)
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        Get Instagram user information
        
        Args:
            user_id: Instagram user ID
            
        Returns:
            Dict with user info or None if failed
        """
        if not user_id:
            logger.error("Missing user_id for get_user_info")
            return None
            
        url = f"{self.base_url}/{user_id}"
        params = {
            "fields": "name,profile_pic,id",
            "access_token": self.access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            user_data = response.json()
            
            logger.info(f"Retrieved user info for {user_id}")
            return user_data
            
        except requests.RequestException as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    def verify_webhook(self, verify_token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook for Instagram
        
        Args:
            verify_token: Token sent by Instagram
            challenge: Challenge string to echo back
            
        Returns:
            Challenge string if verification successful, None otherwise
        """
        if not self.verify_token:
            logger.error("INSTAGRAM_VERIFY_TOKEN not configured")
            return None
            
        if verify_token == self.verify_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.warning(f"Webhook verification failed. Expected: {self.verify_token}, Got: {verify_token}")
            return None
    
    def parse_webhook_message(self, webhook_data: Dict) -> Optional[Dict]:
        """
        Parse incoming webhook message with enhanced error handling
        
        Args:
            webhook_data: Raw webhook data from Instagram
            
        Returns:
            Dict with parsed message data or None if parsing failed
        """
        try:
            if not webhook_data or "entry" not in webhook_data:
                logger.warning("Invalid webhook data structure")
                return None
            
            entries = webhook_data.get("entry", [])
            if not entries:
                logger.warning("No entries in webhook data")
                return None
            
            # Process first entry (Instagram typically sends one)
            entry = entries[0]
            
            # Handle Instagram messaging
            if "messaging" in entry:
                messaging = entry["messaging"]
                if not messaging:
                    return None
                
                message_event = messaging[0]
                
                # Parse text message
                if "message" in message_event:
                    message = message_event["message"]
                    
                    # Handle text messages
                    if "text" in message:
                        parsed_data = {
                            "type": "message",
                            "sender_id": message_event["sender"]["id"],
                            "message_text": message["text"],
                            "timestamp": message_event.get("timestamp", int(datetime.now().timestamp() * 1000)),
                            "message_id": message.get("mid", ""),
                            "is_echo": message_event.get("message", {}).get("is_echo", False)
                        }
                        
                        # Check for quick reply payload
                        if "quick_reply" in message:
                            parsed_data["quick_reply_payload"] = message["quick_reply"].get("payload", "")
                        
                        logger.info(f"Parsed text message from {parsed_data['sender_id']}")
                        return parsed_data
                    
                    # Handle attachments (images, etc.)
                    elif "attachments" in message:
                        attachment = message["attachments"][0]
                        parsed_data = {
                            "type": "attachment",
                            "sender_id": message_event["sender"]["id"],
                            "attachment_type": attachment.get("type", "unknown"),
                            "attachment_url": attachment.get("payload", {}).get("url"),
                            "timestamp": message_event.get("timestamp", int(datetime.now().timestamp() * 1000)),
                            "message_id": message.get("mid", "")
                        }
                        
                        logger.info(f"Parsed attachment from {parsed_data['sender_id']}")
                        return parsed_data
                
                # Handle postback (button clicks)
                elif "postback" in message_event:
                    postback = message_event["postback"]
                    parsed_data = {
                        "type": "postback",
                        "sender_id": message_event["sender"]["id"],
                        "postback_payload": postback.get("payload", ""),
                        "postback_title": postback.get("title", ""),
                        "timestamp": message_event.get("timestamp", int(datetime.now().timestamp() * 1000))
                    }
                    
                    logger.info(f"Parsed postback from {parsed_data['sender_id']}")
                    return parsed_data
            
            # Handle other Instagram webhook events
            elif "changes" in entry:
                # Handle feed changes, comments, etc.
                logger.info("Received Instagram changes webhook (not implemented)")
                return None
            
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error(f"Error parsing webhook message: {e}")
            logger.debug(f"Webhook data: {json.dumps(webhook_data, indent=2)}")
        
        return None
    
    def get_page_access_token(self) -> Optional[str]:
        """
        Get page access token if using user access token
        
        Returns:
            Page access token or None if failed
        """
        url = f"{self.base_url}/{self.page_id}"
        params = {
            "fields": "access_token",
            "access_token": self.access_token
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            page_token = data.get("access_token")
            if page_token:
                logger.info("Successfully retrieved page access token")
                return page_token
            else:
                logger.warning("No access token found in page data")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error getting page access token: {e}")
            return None
    
    def validate_setup(self) -> Dict[str, bool]:
        """
        Validate Instagram client setup
        
        Returns:
            Dict with validation results
        """
        results = {
            "access_token_present": bool(self.access_token),
            "page_id_present": bool(self.page_id),
            "verify_token_present": bool(self.verify_token),
            "can_access_page": False
        }
        
        # Test page access
        if self.access_token and self.page_id:
            try:
                url = f"{self.base_url}/{self.page_id}"
                params = {
                    "fields": "id,name",
                    "access_token": self.access_token
                }
                
                response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    results["can_access_page"] = True
                    page_data = response.json()
                    logger.info(f"Successfully connected to page: {page_data.get('name', 'Unknown')}")
                
            except requests.RequestException as e:
                logger.error(f"Failed to validate page access: {e}")
        
        return results
    
    def log_webhook_data(self, webhook_data: Dict) -> None:
        """
        Log webhook data for debugging (sanitized)
        
        Args:
            webhook_data: Raw webhook data
        """
        try:
            # Create a sanitized version for logging
            sanitized_data = json.loads(json.dumps(webhook_data))
            
            # Remove sensitive data if any
            if "entry" in sanitized_data:
                for entry in sanitized_data["entry"]:
                    if "messaging" in entry:
                        for message in entry["messaging"]:
                            # Keep structure but sanitize content
                            if "sender" in message:
                                sender_id = message["sender"].get("id", "unknown")
                                message["sender"]["id"] = f"user_{hash(sender_id) % 10000}"
            
            logger.debug(f"Webhook data: {json.dumps(sanitized_data, indent=2)}")
            
        except Exception as e:
            logger.warning(f"Failed to log webhook data: {e}")
    
    def is_user_message(self, parsed_message: Dict) -> bool:
        """
        Check if parsed message is from user (not echo)
        
        Args:
            parsed_message: Parsed message data
            
        Returns:
            bool: True if message is from user
        """
        if not parsed_message:
            return False
            
        # Skip echo messages (messages sent by the bot)
        if parsed_message.get("is_echo", False):
            return False
        
        # Skip if no sender_id
        if not parsed_message.get("sender_id"):
            return False
            
        return True