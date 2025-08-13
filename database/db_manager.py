import sqlite3
import json
from typing import List, Optional
from models.booking_models import Booking, ConversationState
from config import Config

class DatabaseManager:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Bookings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    check_in_date TEXT NOT NULL,
                    check_out_date TEXT NOT NULL,
                    room_type TEXT not null,
                    num_guests INTEGER not null,
                    guest_name TEXT not null,
                    guest_email TEXT not null,
                    guest_phone varchar not null,
                    total_price REAL NOT NULL,
                    status TEXT DEFAULT 'confirmed',
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Conversation states table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_states (
                    user_id TEXT PRIMARY KEY,
                    current_step TEXT NOT NULL,
                    booking_data TEXT,
                    last_message TEXT,
                    context TEXT
                )
            ''')
            
            conn.commit()
    
    def save_booking(self, booking: Booking) -> bool:
        """Save booking to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO bookings 
                    (booking_id, user_id, check_in_date, check_out_date, room_type, 
                     num_guests, guest_name, guest_email, guest_phone, total_price, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    booking.booking_id, booking.user_id, booking.check_in_date,
                    booking.check_out_date, booking.room_type, booking.num_guests,
                    booking.guest_name, booking.guest_email, booking.guest_phone,
                    booking.total_price, booking.status, booking.created_at
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving booking: {e}")
            return False
    
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,))
                row = cursor.fetchone()
                
                if row:
                    return Booking(
                        booking_id=row[0], user_id=row[1], check_in_date=row[2],
                        check_out_date=row[3], room_type=row[4], num_guests=row[5],
                        guest_name=row[6], guest_email=row[7], guest_phone=row[8],
                        total_price=row[9], status=row[10], created_at=row[11]
                    )
        except Exception as e:
            print(f"Error getting booking: {e}")
        return None
    
    def get_user_bookings(self, user_id: str) -> List[Booking]:
        """Get all bookings for a user"""
        bookings = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookings WHERE user_id = ?', (user_id,))
                rows = cursor.fetchall()
                
                for row in rows:
                    bookings.append(Booking(
                        booking_id=row[0], user_id=row[1], check_in_date=row[2],
                        check_out_date=row[3], room_type=row[4], num_guests=row[5],
                        guest_name=row[6], guest_email=row[7], guest_phone=row[8],
                        total_price=row[9], status=row[10], created_at=row[11]
                    ))
        except Exception as e:
            print(f"Error getting user bookings: {e}")
        return bookings
    
    def save_conversation_state(self, state: ConversationState) -> bool:
        """Save conversation state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO conversation_states 
                    (user_id, current_step, booking_data, last_message, context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    state.user_id, state.current_step,
                    json.dumps(state.booking_data),
                    state.last_message,
                    json.dumps(state.context)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving conversation state: {e}")
            return False
    
    def get_conversation_state(self, user_id: str) -> Optional[ConversationState]:
        """Get conversation state for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM conversation_states WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return ConversationState(
                        user_id=row[0],
                        current_step=row[1],
                        booking_data=json.loads(row[2] or '{}'),
                        last_message=row[3] or '',
                        context=json.loads(row[4] or '{}')
                    )
        except Exception as e:
            print(f"Error getting conversation state: {e}")
        return None