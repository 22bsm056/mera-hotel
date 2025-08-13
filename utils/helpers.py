from datetime import datetime, timedelta
import re

def validate_date(date_string: str) -> bool:
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def parse_date_from_text(text: str) -> str:
    """Extract date from natural language text"""
    # Simple regex patterns for common date formats
    patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{2}-\d{2}-\d{4}'   # MM-DD-YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            # Convert to standard format
            if '/' in date_str:
                parts = date_str.split('/')
                return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            elif '-' in date_str and len(date_str.split('-')[0]) == 2:
                parts = date_str.split('-')
                return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            else:
                return date_str
    
    return None

def calculate_nights(check_in: str, check_out: str) -> int:
    """Calculate number of nights between dates"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        return (check_out_date - check_in_date).days
    except ValueError:
        return 1

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:.2f}"

def generate_booking_id() -> str:
    """Generate unique booking ID"""
    return f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"

def validate_room_type(room_type: str) -> bool:
    """Validate room type"""
    valid_types = ['standard', 'deluxe', 'suite']
    return room_type.lower() in valid_types

def sanitize_input(text: str) -> str:
    """Basic input sanitization"""
    # Remove potentially harmful characters
    cleaned = re.sub(r'[<>"\']', '', text)
    return cleaned.strip()

def format_booking_summary(booking) -> str:
    """Format booking details for display"""
    return f"""
Booking Summary:
ID: {booking.booking_id}
Check-in: {booking.check_in_date}
 Check-out: {booking.check_out_date}
 Room: {booking.room_type.title()}
Guests: {booking.number_of_guests}
 Total: {format_currency(booking.total_price)}
 Status: {booking.status.title()}
"""