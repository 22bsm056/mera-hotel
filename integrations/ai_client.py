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
    def __init__(self, max_tokens: int = 1000, temperature: float = 0.3):
        self.api_token = os.getenv("GEMINI_API_KEY")
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_token:
            logger.error("GEMINI_API_KEY not found in environment variables. Please ensure it's set.")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=self.api_token)
            # Keep the model selection you used previously (change if needed)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Gemini AI Client initialized successfully with model: 'gemini-2.5-flash'.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def _parse_model_response_text(self, response) -> Optional[str]:
        """
        Robust text extraction from possible Gemini response shapes.
        Tries: response.text, response.result.parts, result.candidates[*].content.parts,
        then falls back to str(response).
        """
        try:
            # 1) Quick accessor (may raise for non-simple responses)
            if hasattr(response, "text"):
                try:
                    txt = response.text
                    if isinstance(txt, str) and txt.strip():
                        return txt.strip()
                except Exception:
                    pass

            # 2) result.parts
            result = getattr(response, "result", None)
            if result is not None:
                parts = getattr(result, "parts", None)
                if parts:
                    collected = []
                    for p in parts:
                        if isinstance(p, dict):
                            # common keys
                            for key in ("text", "content", "payload"):
                                if key in p and isinstance(p[key], str) and p[key].strip():
                                    collected.append(p[key].strip())
                                    break
                        else:
                            txt = getattr(p, "text", None) or getattr(p, "content", None)
                            if isinstance(txt, str) and txt.strip():
                                collected.append(txt.strip())
                    if collected:
                        return "\n".join(collected).strip()

                # 3) result.candidates -> content -> parts
                candidates = getattr(result, "candidates", None)
                if candidates:
                    for cand in candidates:
                        if isinstance(cand, dict):
                            content = cand.get("content")
                        else:
                            content = getattr(cand, "content", None)

                        if not content:
                            continue

                        # content.parts
                        parts = content.get("parts") if isinstance(content, dict) else getattr(content, "parts", None)
                        if parts:
                            collected = []
                            for p in parts:
                                if isinstance(p, dict):
                                    for key in ("text", "content", "payload"):
                                        if key in p and isinstance(p[key], str) and p[key].strip():
                                            collected.append(p[key].strip())
                                            break
                                else:
                                    txt = getattr(p, "text", None) or getattr(p, "content", None)
                                    if isinstance(txt, str) and txt.strip():
                                        collected.append(txt.strip())
                            if collected:
                                return "\n".join(collected).strip()

                        # sometimes content is a list of strings
                        if isinstance(content, list):
                            collected = [c.strip() for c in content if isinstance(c, str) and c.strip()]
                            if collected:
                                return "\n".join(collected).strip()

            # 4) fallback: string representation
            try:
                s = str(response)
                if s and s.strip():
                    return s.strip()
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Error while parsing model response: {e}")

        return None

    def _query(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        try:
            tokens = max_tokens or self.max_tokens
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=tokens,
                temperature=self.temperature
            )

            response = self.model.generate_content(prompt, generation_config=generation_config)

            text = self._parse_model_response_text(response)
            if not text:
                logger.warning("Received an empty or unsupported response shape from the Gemini model.")
                return "I'm having trouble processing your request right now. Please try again later."

            return text.strip()
        except Exception as e:
            logger.error(f"Error querying Gemini: {e} for prompt: '{(prompt[:120] + '...') if len(prompt) > 120 else prompt}'")
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
        """
        Exact-token intent detection: model must return exactly one of the valid tokens.
        If not, default to 'inquiry' (same behavior as your original working code).
        """
        prompt = f"""Analyze this message and determine the user's intent. Respond with ONLY one of these exact words:

INTENTS:
- booking (user wants to make a new reservation)
- reschedule (user wants to change existing booking dates)
- cancel (user wants to cancel a booking)
- inquiry (user asking about hotel info, amenities, policies)
- greeting (user is greeting or starting conversation)

Message: "{message}"

Intent:"""
        
        response = self._query(prompt, max_tokens=100)
        # Keep the strict exact-match behavior you prefer:
        response_normalized = (response or "").lower().strip()
        valid_intents = ['booking', 'reschedule', 'cancel', 'inquiry', 'greeting']
        
        if response_normalized in valid_intents:
            logger.info(f"Detected intent: {response_normalized}")
            return response_normalized
        else:
            logger.warning(f"Unknown intent detected: '{response_normalized}'. Defaulting to 'inquiry'.")
            return 'inquiry'

    def extract_booking_info(self, message: str) -> Dict[str, Any]:
        """Extract booking information with fallback parsing"""
        ai_result = self._extract_booking_info_ai(message)
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
            # Extract JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                normalized_data = self._normalize_booking_data(data)
                logger.info(f"AI extracted booking info: {normalized_data}")
                return normalized_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}. Response: '{response}'")
        except Exception as e:
            logger.error(f"Error in AI extraction: {e}")
        return self._get_empty_booking_data()

    def _extract_booking_info_rules(self, message: str) -> Dict[str, Any]:
        data = self._get_empty_booking_data()
        message_lower = message.lower()
        
        date_patterns = [
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, message)
            dates_found.extend(matches)
        
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
        
        room_types = ["standard", "deluxe", "suite"]
        for room_type in room_types:
            if room_type in message_lower:
                data["room_type"] = room_type
                break
        
        guest_match = re.search(r'(\d+)\s*guest', message_lower)
        if guest_match:
            data["num_guests"] = int(guest_match.group(1))
        
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
        if email_match:
            data["guest_email"] = email_match.group()
        
        phone_match = re.search(r'\b\d{10,12}\b', message)
        if phone_match:
            data["guest_phone"] = phone_match.group()
        
        booking_terms = {"check", "in", "out", "room", "guest", "standard", "deluxe", "suite", 
                        "date", "night", "book", "reservation", "email", "phone", "number"}
        words = re.findall(r'\b[A-Za-z]+\b', message)
        potential_names = [word for word in words if word.lower() not in booking_terms and len(word) > 2]
        
        if len(potential_names) >= 2:
            data["guest_name"] = " ".join(potential_names[:2])
        
        logger.info(f"Rule-based extracted booking info: {data}")
        return data

    def _normalize_date(self, date_str: str) -> Optional[str]:
        try:
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
            
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
                parts = date_str.split('-')
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', date_str):
                separator = '/' if '/' in date_str else '-'
                parts = date_str.split(separator)
                return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                
        except Exception as e:
            logger.error(f"Error normalizing date '{date_str}': {e}")
        
        return None

    def _normalize_booking_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
        
        return self._query(prompt, max_tokens=1000)
