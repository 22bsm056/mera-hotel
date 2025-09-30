import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import json
import google.generativeai as genai
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class AIClient:
    def __init__(self, max_tokens: int = 1000, temperature: float = 0.3):  # Increased tokens, lowered temperature
        self.api_token = os.getenv("GEMINI_API_KEY")
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_token:
            logger.error("GEMINI_API_KEY not found in environment variables. "
                         "Please ensure it's set in your .env file or system environment.")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=self.api_token)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info(f"Gemini AI Client initialized successfully with model: 'gemini-1.5-flash'.")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise

    def _query(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        try:
            tokens = max_tokens or self.max_tokens
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=tokens,
                temperature=self.temperature
            )
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            if not response.text:
                logger.warning("Received an empty response from the Gemini model.")
                return "I'm having trouble processing your request right now. Please try again later."
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error querying Gemini: {str(e)} for prompt: '{prompt[:100]}...'")
            return "I'm having trouble processing your request right now. Please try again later."

    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        base_prompt = """You are a professional hotel booking assistant named Maya. You are helpful, friendly, and knowledgeable about hotel services.

Guidelines:
- Always be polite and professional
- Provide clear, concise responses
- If you don't have specific information, ask for clarification
- Be helpful with hotel-related questions about amenities, policies, check-in/out times, etc.
- Keep responses conversational but informative"""
        
        if context:
            hotel_info = context.get('hotel_info', {})
            if hotel_info:
                hotel_context = f"\nHotel Information: {json.dumps(hotel_info, indent=2)}"
                full_prompt = f"{base_prompt}{hotel_context}\n\nUser Question: {prompt}\n\nResponse:"
            else:
                full_prompt = f"{base_prompt}\n\nUser Question: {prompt}\n\nResponse:"
        else:
            full_prompt = f"{base_prompt}\n\nUser Question: {prompt}\n\nResponse:"
            
        return self._query(full_prompt, max_tokens=300)

    def extract_intent(self, message: str) -> str:
        prompt = f"""Analyze this message and determine the user's intent. Respond with ONLY one of these exact words:

INTENTS:
- booking (user wants to make a new reservation)
- reschedule (user wants to change existing booking dates)
- cancel (user wants to cancel a booking)
- inquiry (user asking about hotel info, amenities, policies)
- greeting (user is greeting or starting conversation)

Message: "{message}"

Intent:"""
        
        response = self._query(prompt, max_tokens=100).lower().strip()
        valid_intents = ['booking', 'reschedule', 'cancel', 'inquiry', 'greeting']
        
        if response in valid_intents:
            logger.info(f"Detected intent: {response}")
            return response
        else:
            logger.warning(f"Unknown intent detected: '{response}'. Defaulting to 'inquiry'.")
            return 'inquiry'

    def extract_booking_info(self, message: str) -> Dict[str, Any]:
        """Extract booking information with fallback parsing"""
        # First try AI extraction
        ai_result = self._extract_booking_info_ai(message)
        
        # If AI fails, use rule-based extraction
        if not any(ai_result.values()):
            logger.info("AI extraction failed, using rule-based extraction")
            return self._extract_booking_info_rules(message)
        
        return ai_result

    def _extract_booking_info_ai(self, message: str) -> Dict[str, Any]:
        prompt = f"""Extract booking information from this message and return a valid JSON object.

Message: "{message}"

Extract these fields (use null for missing info):
- check_in_date: Date in YYYY-MM-DD format
- check_out_date: Date in YYYY-MM-DD format  
- room_type: One of "standard", "deluxe", "suite"
- num_guests: Integer number
- guest_name: Full name as string
- guest_email: Email address as string
- guest_phone: Phone number as string

Return only valid JSON:"""
        
        try:
            response = self._query(prompt, max_tokens=300)
            
            # Clean the response
            response = response.replace("```json", "").replace("```", "").strip()
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                # Validate and normalize the structure
                normalized_data = self._normalize_booking_data(data)
                logger.info(f"AI extracted booking info: {normalized_data}")
                return normalized_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {str(e)}. Response: '{response}'")
        except Exception as e:
            logger.error(f"Error in AI extraction: {str(e)}")
        
        return self._get_empty_booking_data()

    def _extract_booking_info_rules(self, message: str) -> Dict[str, Any]:
        """Rule-based extraction as fallback"""
        data = self._get_empty_booking_data()
        message_lower = message.lower()
        
        # Extract dates
        date_patterns = [
            r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD or YYYY-M-D
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{1,2}\s+\w+\s+\d{4})'  # DD Month YYYY
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, message)
            dates_found.extend(matches)
        
        # Convert and assign dates
        normalized_dates = []
        for date_str in dates_found:
            normalized_date = self._normalize_date(date_str)
            if normalized_date:
                normalized_dates.append(normalized_date)
        
        if len(normalized_dates) >= 2:
            data["check_in_date"] = normalized_dates[0]
            data["check_out_date"] = normalized_dates[1]
        elif len(normalized_dates) == 1:
            if "check in" in message_lower or "checkin" in message_lower:
                data["check_in_date"] = normalized_dates[0]
            elif "check out" in message_lower or "checkout" in message_lower:
                data["check_out_date"] = normalized_dates[0]
        
        # Extract room type
        room_types = ["standard", "deluxe", "suite"]
        for room_type in room_types:
            if room_type in message_lower:
                data["room_type"] = room_type
                break
        
        # Extract number of guests
        guest_match = re.search(r'(\d+)\s*guest', message_lower)
        if guest_match:
            data["num_guests"] = int(guest_match.group(1))
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
        if email_match:
            data["guest_email"] = email_match.group()
        
        # Extract phone
        phone_match = re.search(r'\b\d{10,12}\b', message)
        if phone_match:
            data["guest_phone"] = phone_match.group()
        
        # Extract name (rough heuristic)
        # Look for words that might be names (not in common booking terms)
        booking_terms = {"check", "in", "out", "room", "guest", "standard", "deluxe", "suite", 
                        "date", "night", "book", "reservation", "email", "phone", "number"}
        words = re.findall(r'\b[A-Za-z]+\b', message)
        potential_names = [word for word in words if word.lower() not in booking_terms and len(word) > 2]
        
        if len(potential_names) >= 2:
            data["guest_name"] = " ".join(potential_names[:2])
        
        logger.info(f"Rule-based extracted booking info: {data}")
        return data

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize various date formats to YYYY-MM-DD"""
        try:
            # Handle DD Month YYYY format
            month_map = {
                'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
                'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
                'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
                'august': '08', 'aug': '08', 'september': '09', 'sep': '09',
                'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
                'december': '12', 'dec': '12'
            }
            
            if re.match(r'\d{1,2}\s+\w+\s+\d{4}', date_str):
                parts = date_str.split()
                day = parts[0].zfill(2)
                month = month_map.get(parts[1].lower())
                year = parts[2]
                if month:
                    return f"{year}-{month}-{day}"
            
            # Handle YYYY-MM-DD format (normalize single digits)
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
                parts = date_str.split('-')
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            
            # Handle MM/DD/YYYY or MM-DD-YYYY format
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', date_str):
                separator = '/' if '/' in date_str else '-'
                parts = date_str.split(separator)
                return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                
        except Exception as e:
            logger.error(f"Error normalizing date '{date_str}': {e}")
        
        return None

    def _normalize_booking_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate booking data structure"""
        normalized = self._get_empty_booking_data()
        
        for key, value in data.items():
            if key in normalized and value is not None:
                if key in ["check_in_date", "check_out_date"] and isinstance(value, str):
                    normalized_date = self._normalize_date(value)
                    normalized[key] = normalized_date
                elif key == "room_type" and isinstance(value, str):
                    room_type = value.lower().strip()
                    if room_type in ["standard", "deluxe", "suite"]:
                        normalized[key] = room_type
                elif key == "num_guests":
                    try:
                        normalized[key] = int(value)
                    except (ValueError, TypeError):
                        pass
                else:
                    normalized[key] = str(value).strip() if value else None
        
        return normalized

    def _get_empty_booking_data(self) -> Dict[str, Any]:
        """Return empty booking data structure"""
        return {
            "check_in_date": None,
            "check_out_date": None,
            "room_type": None,
            "num_guests": None,
            "guest_name": None,
            "guest_email": None,
            "guest_phone": None
        }

    def generate_booking_confirmation(self, booking_data: Dict[str, Any]) -> str:
        prompt = f"""Generate a professional and warm hotel booking confirmation message.

Booking Details:
{json.dumps(booking_data, indent=2)}

Include:
1. Confirmation message with booking ID
2. Summary of booking details (dates, room, guests, price)
3. Next steps or contact information
4. Friendly closing

Format as a clear, well-structured message."""
        
        return self._query(prompt, max_tokens=400)
