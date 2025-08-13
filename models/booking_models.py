from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import uuid

@dataclass
class Booking:
    booking_id: str
    user_id: str
    check_in_date: str
    check_out_date: str
    room_type: str
    num_guests: int
    guest_name: str
    guest_email: str
    guest_phone: str
    total_price: float
    status: str = "confirmed"
    created_at: str = None
    updated_at: str = None
    special_requests: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "booking_id": self.booking_id,
            "user_id": self.user_id,
            "check_in_date": self.check_in_date,
            "check_out_date": self.check_out_date,
            "room_type": self.room_type,
            "num_guests": self.num_guests,
            "guest_name": self.guest_name,
            "guest_email": self.guest_email,
            "guest_phone": self.guest_phone,
            "total_price": self.total_price,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "special_requests": self.special_requests
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Booking':
        """Create Booking instance from dictionary"""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert booking to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Booking':
        """Create Booking instance from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

@dataclass
class ConversationState:
    user_id: str
    current_step: str = "greeting"
    booking_data: Dict[str, Any] = field(default_factory=dict)
    last_message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = None
    session_id: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
        if self.session_id is None:
            self.session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    def update_step(self, step: str):
        """Update current step and timestamp"""
        self.current_step = step
        self.last_updated = datetime.now().isoformat()
    
    def add_booking_data(self, key: str, value: Any):
        """Add data to booking_data dictionary"""
        self.booking_data[key] = value
        self.last_updated = datetime.now().isoformat()
    
    def clear_booking_data(self):
        """Clear booking data"""
        self.booking_data = {}
        self.last_updated = datetime.now().isoformat()
    
    def set_context(self, key: str, value: Any):
        """Set context data"""
        self.context[key] = value
        self.last_updated = datetime.now().isoformat()
    
    def get_context(self, key: str, default=None):
        """Get context data"""
        return self.context.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_step": self.current_step,
            "booking_data": self.booking_data,
            "last_message": self.last_message,
            "context": self.context,
            "last_updated": self.last_updated,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create ConversationState instance from dictionary"""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert conversation state to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ConversationState':
        """Create ConversationState instance from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

@dataclass
class UserMessage:
    user_id: str
    message: str
    timestamp: str = None
    intent: str = ""
    message_id: str = None
    response: str = ""
    processed: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.message_id is None:
            self.message_id = f"msg_{uuid.uuid4().hex[:8]}"
    
    def mark_processed(self, response: str = ""):
        """Mark message as processed"""
        self.processed = True
        if response:
            self.response = response
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "message_id": self.message_id,
            "response": self.response,
            "processed": self.processed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserMessage':
        """Create UserMessage instance from dictionary"""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert user message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UserMessage':
        """Create UserMessage instance from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

@dataclass
class HotelRoom:
    room_type: str
    price_per_night: float
    capacity: int
    description: str
    amenities: List[str] = field(default_factory=list)
    available: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_type": self.room_type,
            "price_per_night": self.price_per_night,
            "capacity": self.capacity,
            "description": self.description,
            "amenities": self.amenities,
            "available": self.available
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HotelRoom':
        """Create HotelRoom instance from dictionary"""
        return cls(**data)

@dataclass
class BookingHistory:
    user_id: str
    bookings: List[Booking] = field(default_factory=list)
    total_bookings: int = 0
    last_booking_date: str = None
    
    def add_booking(self, booking: Booking):
        """Add a booking to history"""
        self.bookings.append(booking)
        self.total_bookings = len(self.bookings)
        self.last_booking_date = booking.created_at
    
    def get_active_bookings(self) -> List[Booking]:
        """Get all active (confirmed) bookings"""
        return [booking for booking in self.bookings if booking.status == "confirmed"]
    
    def get_cancelled_bookings(self) -> List[Booking]:
        """Get all cancelled bookings"""
        return [booking for booking in self.bookings if booking.status == "cancelled"]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "bookings": [booking.to_dict() for booking in self.bookings],
            "total_bookings": self.total_bookings,
            "last_booking_date": self.last_booking_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookingHistory':
        """Create BookingHistory instance from dictionary"""
        bookings = [Booking.from_dict(booking_data) for booking_data in data.get("bookings", [])]
        return cls(
            user_id=data["user_id"],
            bookings=bookings,
            total_bookings=data.get("total_bookings", 0),
            last_booking_date=data.get("last_booking_date")
        )

# Utility functions
def generate_booking_id() -> str:
    """Generate a unique booking ID"""
    return f"BK{uuid.uuid4().hex[:8].upper()}"

def validate_booking_data(booking_data: Dict[str, Any]) -> List[str]:
    """Validate booking data and return list of missing fields"""
    required_fields = [
        "check_in_date", "check_out_date", "room_type", 
        "num_guests", "guest_name", "guest_email", "guest_phone"
    ]
    
    missing_fields = []
    for field in required_fields:
        if not booking_data.get(field):
            missing_fields.append(field)
    
    return missing_fields

def calculate_total_price(room_price: float, check_in: str, check_out: str) -> float:
    """Calculate total price based on room price and dates"""
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (check_out_date - check_in_date).days
        return max(room_price * nights, 0.0)  # Ensure non-negative price
    except ValueError:
        return 0.0
