import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Instagram API configuration
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")

def send_instagram_message(recipient_id, message_text):
    """
    Send a message to a user on Instagram
    """
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}/messages"
    
    params = {
        "access_token": INSTAGRAM_ACCESS_TOKEN,
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": message_text}
    }
    
    try:
        response = requests.post(url, json=params)
        response.raise_for_status()
        print("Message sent successfully!")
        print("Response:", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error sending message:", e)
        print("Response content:", e.response.text if hasattr(e, 'response') else None)
        return None

def get_instagram_user_id(username):
    """
    Get Instagram user ID from username (requires business discovery permission)
    """
    url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_PAGE_ID}"
    
    params = {
        "access_token": INSTAGRAM_ACCESS_TOKEN,
        "fields": f"business_discovery.username({username}){{id}}"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        user_id = data['business_discovery']['id']
        print(f"User ID for @{username}: {user_id}")
        return user_id
    except requests.exceptions.RequestException as e:
        print("Error getting user ID:", e)
        print("Response content:", e.response.text if hasattr(e, 'response') else None)
        return None

if __name__ == "__main__":
    print("Instagram Message Sender")
    print("1. Send message to existing conversation")
    print("2. Lookup user ID by username")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        recipient_id = input("Enter recipient Instagram user ID: ")
        message_text = input("Enter message text: ")
        send_instagram_message(recipient_id, message_text)
    elif choice == "2":
        username = input("Enter Instagram username (without @): ")
        get_instagram_user_id(username)
    else:
        print("Invalid choice")