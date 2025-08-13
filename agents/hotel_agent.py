from typing import Dict, Any, Optional
from datetime import datetime
from models.booking_models import Booking, ConversationState, generate_booking_id, validate_booking_data, calculate_total_price
from database.db_manager import DatabaseManager
from integrations.ai_client import AIClient
from integrations.instagram_client import InstagramClient
from config import Config
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

class HotelAgent:
    def __init__(self):
        self.db = DatabaseManager()
        self.ai = AIClient()
        self.instagram = InstagramClient()
        self.hotel_info = self._load_hotel_data()
    
    def _load_hotel_data(self) -> dict:
        try:
            hotel_data_path = "data/hotel_data.json"
            if os.path.exists(hotel_data_path):
                with open(hotel_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_fallback_hotel_data()
        except Exception as e:
            logger.error(f"Error loading hotel data: {e}")
            return self._get_fallback_hotel_data()
    
    def _get_fallback_hotel_data(self) -> dict:
        return {
            "name": "Grand Hotel",
            "room_types": {
                "standard": {"price": 100.0, "capacity": 2, "description": "Comfortable standard room with modern amenities"},
                "deluxe": {"price": 150.0, "capacity": 3, "description": "Spacious deluxe room with city view and premium facilities"},
                "suite": {"price": 250.0, "capacity": 4, "description": "Luxurious suite with separate living area and premium services"}
            },
            "amenities": ["Free WiFi", "Swimming Pool", "Fitness Center", "Restaurant", "24/7 Room Service", "Spa", "Business Center"],
            "policies": {
                "check_in": "3:00 PM",
                "check_out": "11:00 AM",
                "cancellation": "Free cancellation up to 24 hours before check-in",
                "pet_policy": "Pet-friendly with additional fee",
                "smoking": "Non-smoking property"
            }
        }
    
    def process_message(self, user_id: str, message: str) -> str:
        try:
            if not user_id or not message:
                return "I didn't receive your message properly. Please try again."
                
            message = message.strip()
            if len(message) > 1000:
                return "Please keep your message under 1000 characters."
                
            state = self.db.get_conversation_state(user_id) or ConversationState(user_id=user_id)
            state.last_message = message
            
            intent = self.ai.extract_intent(message)
            logger.info(f"Processing message from {user_id}: intent={intent}")
            
            response = self._route_to_handler(intent, state)
            
            self.db.save_conversation_state(state)
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I encountered an error processing your request. Please try again later."
    
    def _route_to_handler(self, intent: str, state: ConversationState) -> str:
        handlers = {
            "greeting": self._handle_greeting,
            "booking": self._handle_booking,
            "reschedule": self._handle_reschedule,
            "cancel": self._handle_cancel,
            "inquiry": self._handle_inquiry
        }
        
        handler = handlers.get(intent, self._handle_inquiry)
        return handler(state)
    
    def _handle_greeting(self, state: ConversationState) -> str:
        state.update_step("greeting")
        hotel_name = self.hotel_info.get("name", "our hotel")
        return f"Hello! Welcome to {hotel_name}! \n\nI'm Maya, your booking assistant. I can help you with:\n• Making new reservations\n• Checking room availability\n• Answering questions about amenities\n• Managing existing bookings\n\nHow can I assist you today?"
    
    def _handle_booking(self, state: ConversationState) -> str:
        try:
            if state.current_step in ["greeting", "inquiry"]:
                return self._start_booking_flow(state)
            return self._process_booking_details(state)
        except Exception as e:
            logger.error(f"Error in booking handler: {e}")
            return "I encountered an error while processing your booking. Please try again."
    
    def _start_booking_flow(self, state: ConversationState) -> str:
        state.update_step("get_booking_details")
        room_types = self.hotel_info.get("room_types", {})
        
        if not room_types:
            return "I'm sorry, but room information is currently unavailable. Please try again later."
        
        room_details = []
        for room_type, details in room_types.items():
            room_details.append(f"• {room_type.title()}: ${details['price']}/night (up to {details['capacity']} guests)")
        
        rooms_text = ", ".join([r.title() for r in room_types.keys()])
        
        return f"Perfect! I'd love to help you book a room. \n\nHere are our available rooms:\n" + "\n".join(room_details) + f"\n\nTo proceed, please provide:\n• Check-in date (YYYY-MM-DD)\n• Check-out date (YYYY-MM-DD)\n• Room type ({rooms_text})\n• Number of guests\n• Your full name\n• Email address\n• Phone number\n\nYou can provide all details in one message or step by step!"
    
    def _process_booking_details(self, state: ConversationState) -> str:
        try:
            booking_info = self.ai.extract_booking_info(state.last_message)
            logger.info(f"Extracted booking info: {booking_info}")
            
            for key, value in booking_info.items():
                if value is not None and str(value).strip():
                    state.add_booking_data(key, value)
            
            validation_error = self._validate_booking_input(state.booking_data)
            if validation_error:
                return validation_error
            
            missing = validate_booking_data(state.booking_data)
            if missing:
                return self._request_missing_info(missing, state.booking_data)
            
            return self._create_booking(state)
            
        except Exception as e:
            logger.error(f"Error processing booking details: {e}")
            return "I encountered an error while processing your booking details. Please try again."
    
    def _validate_booking_input(self, booking_data: dict) -> Optional[str]:
        if booking_data.get("check_in_date") and booking_data.get("check_out_date"):
            if not self._validate_dates(booking_data["check_in_date"], booking_data["check_out_date"]):
                return "Please check your dates. The check-out date must be after the check-in date, and both dates should be in the future."
        
        if booking_data.get("room_type"):
            room_type = booking_data["room_type"].lower()
            available_rooms = self.hotel_info.get("room_types", {})
            if room_type not in available_rooms:
                available_list = ", ".join([r.title() for r in available_rooms.keys()])
                return f" '{room_type}' is not available. Our available room types are: {available_list}"
        
        if booking_data.get("num_guests"):
            try:
                guests = int(booking_data["num_guests"])
                if guests < 1 or guests > 10:
                    return "Number of guests must be between 1 and 10."
            except (ValueError, TypeError):
                return "Please provide a valid number of guests."
        
        return None
    
    def _validate_dates(self, check_in: str, check_out: str) -> bool:
        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
            today = datetime.now().date()
            
            return (check_in_date.date() >= today and 
                   check_out_date > check_in_date)
        except ValueError:
            return False
    
    def _request_missing_info(self, missing: list, current_data: dict) -> str:
        field_mapping = {
            "check_in_date": "Check-in date (YYYY-MM-DD)",
            "check_out_date": "Check-out date (YYYY-MM-DD)", 
            "room_type": "Room type",
            "num_guests": "Number of guests",
            "guest_name": "Your full name",
            "guest_email": "Your email address",
            "guest_phone": "Your phone number"
        }
        
        collected_info = []
        for key, value in current_data.items():
            if value and key in field_mapping:
                display_value = str(value).title() if key == "room_type" else str(value)
                collected_info.append(f"✅ {field_mapping[key]}: {display_value}")
        
        missing_info = [f" {field_mapping.get(field, field)}" for field in missing]
        
        response = "Great! I have the following information:\n" + "\n".join(collected_info)
        response += "\n\nI still need:\n" + "\n".join(missing_info)
        response += "\n\nPlease provide the missing details."
        
        return response
    
    def _create_booking(self, state: ConversationState) -> str:
        try:
            room_type = state.booking_data["room_type"].lower()
            room_info = self.hotel_info["room_types"][room_type]
            
            total_price = calculate_total_price(
                room_info["price"], 
                state.booking_data["check_in_date"], 
                state.booking_data["check_out_date"]
            )
            
            if total_price <= 0:
                return "Please check your dates. There seems to be an issue with the date calculation."
            
            booking = Booking(
                booking_id=generate_booking_id(),
                user_id=state.user_id,
                check_in_date=state.booking_data["check_in_date"],
                check_out_date=state.booking_data["check_out_date"],
                room_type=room_type,
                num_guests=int(state.booking_data["num_guests"]),
                guest_name=state.booking_data["guest_name"],
                guest_email=state.booking_data["guest_email"],
                guest_phone=state.booking_data["guest_phone"],
                total_price=total_price
            )
            
            if self.db.save_booking(booking):
                state.update_step("booking_complete")
                state.clear_booking_data()
                return self._generate_booking_confirmation(booking)
            else:
                return " I'm sorry, there was an error saving your booking. Please try again or contact us directly."
                
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return " I encountered an error while creating your booking. Please try again."
    
    def _generate_booking_confirmation(self, booking: Booking) -> str:
        nights = calculate_total_price(1, booking.check_in_date, booking.check_out_date)
        policies = self.hotel_info.get('policies', {})
        
        return f" Booking Confirmed!\n\n **Booking Details:**\n• Booking ID: **{booking.booking_id}**\n• Guest: {booking.guest_name}\n• Dates: {booking.check_in_date} to {booking.check_out_date} ({int(nights)} nights)\n• Room: {booking.room_type.title()}\n• Guests: {booking.num_guests}\n• Total: ${booking.total_price:.2f}\n\n A confirmation email will be sent to {booking.guest_email}\n\n**Check-in:** {policies.get('check_in', '3:00 PM')}\n**Check-out:** {policies.get('check_out', '11:00 AM')}\n\nThank you for choosing {self.hotel_info.get('name', 'our hotel')}! Is there anything else I can help you with?"
    
    def _handle_reschedule(self, state: ConversationState) -> str:
        try:
            if state.current_step == "reschedule_requested":
                return self._process_reschedule_request(state)
            
            bookings = self.db.get_user_bookings(state.user_id)
            active_bookings = [b for b in bookings if b.status == "confirmed"]
            
            if not active_bookings:
                return "You don't have any active bookings to reschedule. Would you like to make a new booking instead?"
            
            state.update_step("reschedule_requested")
            return self._show_reschedule_options(active_bookings)
            
        except Exception as e:
            logger.error(f"Error in reschedule handler: {e}")
            return "I encountered an error while retrieving your bookings. Please try again."
    
    def _show_reschedule_options(self, active_bookings: list) -> str:
        if len(active_bookings) == 1:
            booking = active_bookings[0]
            return f"I found your booking:\n\n **{booking.booking_id}**\n• Dates: {booking.check_in_date} to {booking.check_out_date}\n• Room: {booking.room_type.title()}\n• Guests: {booking.num_guests}\n\nPlease provide your new preferred dates (check-in and check-out in YYYY-MM-DD format)."
        else:
            booking_list = []
            for i, booking in enumerate(active_bookings[:5], 1):
                booking_list.append(f"{i}. **{booking.booking_id}** - {booking.check_in_date} to {booking.check_out_date} ({booking.room_type.title()})")
            
            return f"You have multiple bookings:\n\n" + "\n".join(booking_list) + "\n\nPlease specify which booking ID you'd like to reschedule and provide the new dates."
    
    def _process_reschedule_request(self, state: ConversationState) -> str:
        message = state.last_message.lower()
        booking_info = self.ai.extract_booking_info(state.last_message)
        
        booking_id_pattern = r'bk[a-zA-Z0-9]+'
        booking_id_match = re.search(booking_id_pattern, message, re.IGNORECASE)
        
        if booking_id_match:
            booking_id = booking_id_match.group().upper()
            booking = self.db.get_booking(booking_id)
            
            if not booking or booking.user_id != state.user_id:
                return "Booking not found or you don't have permission to modify it."
            
            if booking_info.get("check_in_date") and booking_info.get("check_out_date"):
                if self._validate_dates(booking_info["check_in_date"], booking_info["check_out_date"]):
                    booking.check_in_date = booking_info["check_in_date"]
                    booking.check_out_date = booking_info["check_out_date"]
                    booking.update_timestamp()
                    
                    room_info = self.hotel_info["room_types"][booking.room_type]
                    booking.total_price = calculate_total_price(
                        room_info["price"], 
                        booking.check_in_date, 
                        booking.check_out_date
                    )
                    
                    if self.db.save_booking(booking):
                        state.update_step("inquiry")
                        return f"Booking rescheduled successfully!\n\n **Updated Booking:**\n• Booking ID: {booking.booking_id}\n• New dates: {booking.check_in_date} to {booking.check_out_date}\n• Updated total: ${booking.total_price:.2f}\n\nIs there anything else I can help you with?"
                    else:
                        return " Error updating booking. Please try again."
                else:
                    return " Invalid dates. Please ensure check-out is after check-in and both dates are in the future."
            else:
                return "Please provide both check-in and check-out dates in YYYY-MM-DD format."
        else:
            return "Please provide the booking ID and new dates you'd like to reschedule to."
    
    def _handle_cancel(self, state: ConversationState) -> str:
        try:
            if "confirm cancel" in state.last_message.lower():
                return self._process_cancellation(state)
            
            bookings = self.db.get_user_bookings(state.user_id)
            active_bookings = [b for b in bookings if b.status == "confirmed"]
            
            if not active_bookings:
                return "You don't have any active bookings to cancel."
            
            state.update_step("cancel_requested")
            return self._show_cancellation_options(active_bookings)
            
        except Exception as e:
            logger.error(f"Error in cancel handler: {e}")
            return "I encountered an error while retrieving your bookings. Please try again."
    
    def _show_cancellation_options(self, active_bookings: list) -> str:
        cancellation_policy = self.hotel_info.get('policies', {}).get('cancellation', 'Please contact us for cancellation terms')
        
        if len(active_bookings) == 1:
            booking = active_bookings[0]
            return f"I found your booking:\n\n **{booking.booking_id}**\n• Dates: {booking.check_in_date} to {booking.check_out_date}\n• Room: {booking.room_type.title()}\n• Total: ${booking.total_price:.2f}\n\n⚠️ **Cancellation Policy:** {cancellation_policy}\n\nType 'CONFIRM CANCEL' if you want to proceed with cancelling this booking."
        else:
            booking_list = []
            for i, booking in enumerate(active_bookings[:5], 1):
                booking_list.append(f"{i}. **{booking.booking_id}** - {booking.check_in_date} to {booking.check_out_date} (${booking.total_price:.2f})")
            
            return f"You have multiple bookings:\n\n" + "\n".join(booking_list) + "\n\nPlease specify which booking ID you'd like to cancel."
    
    def _process_cancellation(self, state: ConversationState) -> str:
        bookings = self.db.get_user_bookings(state.user_id)
        active_bookings = [b for b in bookings if b.status == "confirmed"]
        
        if not active_bookings:
            return "No active bookings found to cancel."
        
        if len(active_bookings) == 1:
            booking = active_bookings[0]
            booking.status = "cancelled"
            booking.update_timestamp()
            
            if self.db.save_booking(booking):
                state.update_step("inquiry")
                return f" Booking cancelled successfully!\n\n **Cancelled Booking:**\n• Booking ID: {booking.booking_id}\n• Dates: {booking.check_in_date} to {booking.check_out_date}\n• Amount: ${booking.total_price:.2f}\n\nYou will receive a cancellation confirmation email shortly. Is there anything else I can help you with?"
            else:
                return "Error cancelling booking. Please try again or contact us directly."
        else:
            return "Please specify which booking ID you'd like to cancel."
    
    def _handle_inquiry(self, state: ConversationState) -> str:
        try:
            message_lower = state.last_message.lower()
            
            if any(word in message_lower for word in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
                return self._handle_greeting(state)
            
            if any(word in message_lower for word in ['amenities', 'facilities', 'services']):
                return self._get_amenities_info()
            
            if any(word in message_lower for word in ['check-in', 'check-out', 'policy', 'policies']):
                return self._get_policies_info()
            
            if any(word in message_lower for word in ['room', 'rooms', 'price', 'cost']):
                return self._get_room_info()
            
            response = self.ai.generate_response(state.last_message, {
                "hotel_info": self.hotel_info,
                "user_id": state.user_id
            })
            
            if len(response) < 50:
                response += f"\n\nI can also help you with:\n• Room bookings and availability\n• Hotel amenities and services\n• Booking modifications\n• General hotel information"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in inquiry handler: {e}")
            return self._get_default_help_message()
    
    def _get_amenities_info(self) -> str:
        amenities = self.hotel_info.get('amenities', [])
        amenities_text = "\n• ".join(amenities) if amenities else "Various amenities available"
        return f" **{self.hotel_info.get('name', 'Our Hotel')} Amenities:**\n\n• {amenities_text}\n\nWould you like to know more about any specific amenity or make a booking?"
    
    def _get_policies_info(self) -> str:
        policies = self.hotel_info.get('policies', {})
        policy_text = []
        
        for key, value in policies.items():
            formatted_key = key.replace('_', ' ').title()
            policy_text.append(f"• **{formatted_key}:** {value}")
        
        policies_display = "\n".join(policy_text) if policy_text else "Standard hotel policies apply"
        return f" **Hotel Policies:**\n\n{policies_display}\n\nDo you have any specific questions about our policies?"
    
    def _get_room_info(self) -> str:
        room_types = self.hotel_info.get('room_types', {})
        if not room_types:
            return "Room information is currently unavailable. Please contact us directly."
        
        room_details = []
        for room_type, details in room_types.items():
            room_details.append(f"**{room_type.title()}**\n  Price: ${details['price']}/night\n  Capacity: Up to {details['capacity']} guests\n  {details['description']}")
        
        return f" **Available Rooms:**\n\n" + "\n\n".join(room_details) + "\n\nWould you like to make a reservation?"
    
    def _get_default_help_message(self) -> str:
        amenities = self.hotel_info.get('amenities', ['WiFi', 'Pool', 'Restaurant'])
        amenities_preview = ', '.join(amenities[:3])
        if len(amenities) > 3:
            amenities_preview += f", and {len(amenities) - 3} more"
        
        return f"I'm here to help with your hotel needs! You can ask me about:\n\n• Room types and pricing\n• Hotel amenities: {amenities_preview}\n• Check-in/out times and policies\n• Making a reservation\n• Managing existing bookings\n\nWhat would you like to know?"