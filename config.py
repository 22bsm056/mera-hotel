import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
    INSTAGRAM_VERIFY_TOKEN= os.getenv("INSTAGRAM_VERIFY_TOKEN")
    INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
    HUGGINGFACE_API_KEY =  os.getenv("HUGGINGFACE_API_KEY")
    
    # Hotel Configuration
    HOTEL_NAME = "Grand Palace Hotel"
    HOTEL_ADDRESS = "123 Luxury Street, City Center"
    CHECK_IN_TIME = "3:00 PM"
    CHECK_OUT_TIME = "11:00 AM"
    
    # Database
    DATABASE_PATH = "hotel_bookings.db"