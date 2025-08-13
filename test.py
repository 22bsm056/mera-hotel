#!/usr/bin/env python3
"""
Hotel Booking AI Agent - Comprehensive Test Script
Tests all major functionalities before Instagram integration
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HotelAgentTester:
    def __init__(self):
        self.test_results = []
        self.test_user_id = "test_user_123"
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup test environment and dependencies"""
        print("🔧 Setting up test environment...")
        
        try:
            # Import project modules
            from agents.hotel_agent import HotelAgent
            from database.db_manager import DatabaseManager
            from integrations.ai_client import AIClient
            from integrations.instagram_client import InstagramClient
            from models.booking_models import Booking, ConversationState
            from config import Config
            
            self.agent = HotelAgent()
            self.db = DatabaseManager()
            self.ai = AIClient()
            self.instagram = InstagramClient()
            
            print("✅ All modules imported successfully")
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure all dependencies are installed and modules are in correct paths")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Setup error: {e}")
            sys.exit(1)
    
    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Run a single test and record results"""
        print(f"\n🧪 Testing: {test_name}")
        print("-" * 50)
        
        try:
            start_time = time.time()
            result = test_func(*args, **kwargs)
            end_time = time.time()
            
            self.test_results.append({
                "test": test_name,
                "status": "PASS" if result else "FAIL",
                "duration": round(end_time - start_time, 2),
                "result": result
            })
            
            if result:
                print(f"✅ {test_name} - PASSED ({end_time - start_time:.2f}s)")
            else:
                print(f"❌ {test_name} - FAILED ({end_time - start_time:.2f}s)")
                
            return result
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "ERROR",
                "duration": 0,
                "error": str(e)
            })
            print(f"💥 {test_name} - ERROR: {e}")
            logger.error(f"Test {test_name} failed with error: {e}")
            return False
    
    def test_database_connection(self):
        """Test database initialization and basic operations"""
        try:
            # Test database creation
            if not os.path.exists(self.db.db_path):
                print("❌ Database file not found")
                return False
            
            # Test table creation
            cursor = self.db.get_connection().cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            expected_tables = ['bookings', 'conversation_states']
            existing_tables = [table[0] for table in tables]
            
            for table in expected_tables:
                if table not in existing_tables:
                    print(f"❌ Table '{table}' not found")
                    return False
            
            print("✅ Database and tables exist")
            return True
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return False
    
    def test_ai_client_initialization(self):
        """Test AI client setup and basic functionality"""
        try:
            # Test initialization
            if not hasattr(self.ai, 'model'):
                print("❌ AI model not initialized")
                return False
            
            # Test basic query
            response = self.ai.generate_response("Hello, test message")
            if not response or len(response) < 10:
                print("❌ AI response too short or empty")
                return False
            
            print(f"✅ AI response: {response[:100]}...")
            return True
            
        except Exception as e:
            print(f"❌ AI client test failed: {e}")
            return False
    
    def test_intent_extraction(self):
        """Test AI intent extraction functionality"""
        test_cases = [
            ("I want to book a room", "booking"),
            ("Hello there", "greeting"),
            ("What amenities do you have?", "inquiry"),
            ("I need to reschedule my booking", "reschedule"),
            ("Cancel my reservation", "cancel")
        ]
        
        all_passed = True
        for message, expected_intent in test_cases:
            try:
                detected_intent = self.ai.extract_intent(message)
                if detected_intent == expected_intent:
                    print(f"✅ '{message}' -> {detected_intent}")
                else:
                    print(f"❌ '{message}' -> Expected: {expected_intent}, Got: {detected_intent}")
                    all_passed = False
            except Exception as e:
                print(f"❌ Intent extraction failed for '{message}': {e}")
                all_passed = False
        
        return all_passed
    
    def test_booking_info_extraction(self):
        """Test booking information extraction from messages"""
        test_message = "I want to book a deluxe room for 2 guests from 2024-12-25 to 2024-12-28. My name is John Doe, email john@example.com, phone 123-456-7890"
        
        try:
            booking_info = self.ai.extract_booking_info(test_message)
            
            expected_fields = {
                "room_type": "deluxe",
                "num_guests": 2,
                "guest_name": "John Doe",
                "guest_email": "john@example.com",
                "guest_phone": "123-456-7890"
            }
            
            all_correct = True
            for field, expected_value in expected_fields.items():
                actual_value = booking_info.get(field)
                if str(actual_value).lower() != str(expected_value).lower():
                    print(f"❌ {field}: Expected '{expected_value}', Got '{actual_value}'")
                    all_correct = False
                else:
                    print(f"✅ {field}: {actual_value}")
            
            return all_correct
            
        except Exception as e:
            print(f"❌ Booking info extraction failed: {e}")
            return False
    
    def test_conversation_flow_greeting(self):
        """Test greeting conversation flow"""
        try:
            response = self.agent.process_message(self.test_user_id, "Hello!")
            
            if "welcome" in response.lower() or "hello" in response.lower():
                print(f"✅ Greeting response: {response[:100]}...")
                return True
            else:
                print(f"❌ Unexpected greeting response: {response}")
                return False
                
        except Exception as e:
            print(f"❌ Greeting test failed: {e}")
            return False
    
    def test_conversation_flow_inquiry(self):
        """Test inquiry conversation flow"""
        test_questions = [
            "What amenities do you have?",
            "What are your room types?",
            "What time is check-in?"
        ]
        
        all_passed = True
        for question in test_questions:
            try:
                response = self.agent.process_message(self.test_user_id, question)
                if len(response) > 20:
                    print(f"✅ '{question}' -> Response received ({len(response)} chars)")
                else:
                    print(f"❌ '{question}' -> Response too short: {response}")
                    all_passed = False
            except Exception as e:
                print(f"❌ Inquiry test failed for '{question}': {e}")
                all_passed = False
        
        return all_passed
    
    def test_booking_flow_complete(self):
        """Test complete booking flow"""
        try:
            # Generate future dates
            check_in = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            check_out = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
            
            # Start booking
            response1 = self.agent.process_message(self.test_user_id, "I want to book a room")
            print(f"📝 Booking start: {response1[:100]}...")
            
            # Provide complete booking info
            booking_message = f"I want to book a standard room for 2 guests from {check_in} to {check_out}. My name is Test User, email test@example.com, phone 555-0123"
            response2 = self.agent.process_message(self.test_user_id, booking_message)
            print(f"📝 Booking details: {response2[:100]}...")
            
            # Check if booking was confirmed
            if "confirmed" in response2.lower() or "booking id" in response2.lower():
                print("✅ Booking flow completed successfully")
                return True
            else:
                print(f"❌ Booking not confirmed. Response: {response2}")
                return False
                
        except Exception as e:
            print(f"❌ Complete booking test failed: {e}")
            return False
    
    def test_database_operations(self):
        """Test database CRUD operations"""
        try:
            from models.booking_models import Booking, ConversationState, generate_booking_id
            
            # Test conversation state save/load
            state = ConversationState(user_id="test_db_user")
            state.add_booking_data("test_key", "test_value")
            
            # Save state
            if not self.db.save_conversation_state(state):
                print("❌ Failed to save conversation state")
                return False
            
            # Load state
            loaded_state = self.db.get_conversation_state("test_db_user")
            if not loaded_state or loaded_state.booking_data.get("test_key") != "test_value":
                print("❌ Failed to load conversation state correctly")
                return False
            
            # Test booking save/load
            booking = Booking(
                booking_id=generate_booking_id(),
                user_id="test_db_user",
                check_in_date="2024-12-25",
                check_out_date="2024-12-28",
                room_type="standard",
                num_guests=2,
                guest_name="Test User",
                guest_email="test@example.com",
                guest_phone="555-0123",
                total_price=300.0
            )
            
            # Save booking
            if not self.db.save_booking(booking):
                print("❌ Failed to save booking")
                return False
            
            # Load booking
            loaded_booking = self.db.get_booking(booking.booking_id)
            if not loaded_booking or loaded_booking.guest_name != "Test User":
                print("❌ Failed to load booking correctly")
                return False
            
            print("✅ Database operations successful")
            return True
            
        except Exception as e:
            print(f"❌ Database operations test failed: {e}")
            return False
    
    def test_hotel_data_loading(self):
        """Test hotel data loading and structure"""
        try:
            hotel_info = self.agent.hotel_info
            
            # Check required fields
            required_fields = ['name', 'room_types', 'amenities', 'policies']
            for field in required_fields:
                if field not in hotel_info:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Check room types structure
            room_types = hotel_info['room_types']
            if not isinstance(room_types, dict) or len(room_types) == 0:
                print("❌ Invalid room types structure")
                return False
            
            for room_type, details in room_types.items():
                required_room_fields = ['price', 'capacity', 'description']
                for field in required_room_fields:
                    if field not in details:
                        print(f"❌ Missing room field {field} in {room_type}")
                        return False
            
            print(f"✅ Hotel data loaded: {hotel_info['name']}")
            print(f"✅ Room types: {list(room_types.keys())}")
            print(f"✅ Amenities count: {len(hotel_info['amenities'])}")
            return True
            
        except Exception as e:
            print(f"❌ Hotel data test failed: {e}")
            return False
    
    def test_instagram_client_setup(self):
        """Test Instagram client initialization"""
        try:
            # Test client initialization
            if not hasattr(self.instagram, 'access_token'):
                print("❌ Instagram access token not found")
                return False
            
            # Test validation
            validation_results = self.instagram.validate_setup()
            
            print("📱 Instagram Setup Validation:")
            for key, value in validation_results.items():
                status = "✅" if value else "❌"
                print(f"  {status} {key.replace('_', ' ').title()}: {value}")
            
            # Instagram setup is optional for local testing
            if not validation_results.get('access_token_present'):
                print("⚠️  Instagram not configured - this is OK for local testing")
                return True
            
            return all(validation_results.values())
            
        except Exception as e:
            print(f"❌ Instagram client test failed: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        try:
            # Test empty message
            response1 = self.agent.process_message(self.test_user_id, "")
            if "didn't receive" not in response1.lower():
                print("❌ Empty message not handled properly")
                return False
            
            # Test very long message
            long_message = "a" * 1500
            response2 = self.agent.process_message(self.test_user_id, long_message)
            if "under 1000 characters" not in response2.lower():
                print("❌ Long message not handled properly")
                return False
            
            # Test invalid user ID
            response3 = self.agent.process_message("", "Hello")
            if "didn't receive" not in response3.lower():
                print("❌ Invalid user ID not handled properly")
                return False
            
            print("✅ Error handling working correctly")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def test_webhook_parsing(self):
        """Test Instagram webhook message parsing"""
        try:
            # Sample webhook data
            sample_webhook = {
                "entry": [{
                    "messaging": [{
                        "sender": {"id": "test_sender_123"},
                        "message": {
                            "text": "Hello, I want to book a room",
                            "mid": "test_message_id"
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    }]
                }]
            }
            
            parsed = self.instagram.parse_webhook_message(sample_webhook)
            
            if not parsed:
                print("❌ Failed to parse webhook message")
                return False
            
            if parsed.get("type") != "message":
                print(f"❌ Wrong message type: {parsed.get('type')}")
                return False
            
            if parsed.get("message_text") != "Hello, I want to book a room":
                print(f"❌ Wrong message text: {parsed.get('message_text')}")
                return False
            
            print("✅ Webhook parsing successful")
            return True
            
        except Exception as e:
            print(f"❌ Webhook parsing test failed: {e}")
            return False
    
    def run_integration_test(self):
        """Run a complete integration test simulating a user conversation"""
        print("\n🔄 Running Integration Test - Complete User Journey")
        print("=" * 60)
        
        test_user = "integration_test_user"
        
        try:
            # 1. Greeting
            response1 = self.agent.process_message(test_user, "Hi there!")
            print(f"1️⃣ Greeting: {response1[:80]}...")
            
            # 2. Inquiry about rooms
            response2 = self.agent.process_message(test_user, "What room types do you have?")
            print(f"2️⃣ Room inquiry: {response2[:80]}...")
            
            # 3. Start booking
            response3 = self.agent.process_message(test_user, "I want to book a room")
            print(f"3️⃣ Booking start: {response3[:80]}...")
            
            # 4. Provide booking details
            future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
            future_date_out = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
            
            booking_details = f"Book a deluxe room for 2 guests from {future_date} to {future_date_out}. Name: Integration Test, email: integration@test.com, phone: 555-9999"
            response4 = self.agent.process_message(test_user, booking_details)
            print(f"4️⃣ Booking details: {response4[:80]}...")
            
            # 5. Check if booking was successful
            if "confirmed" in response4.lower() or "booking id" in response4.lower():
                print("✅ Integration test completed successfully!")
                return True
            else:
                print("❌ Integration test failed - booking not confirmed")
                return False
                
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Remove test bookings
            cursor.execute("DELETE FROM bookings WHERE user_id LIKE 'test%' OR user_id LIKE 'integration%'")
            
            # Remove test conversation states
            cursor.execute("DELETE FROM conversation_states WHERE user_id LIKE 'test%' OR user_id LIKE 'integration%'")
            
            conn.commit()
            print("🧹 Test data cleaned up")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def generate_test_report(self):
        """Generate and display test report"""
        print("\n" + "=" * 60)
        print("📊 TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'PASS'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'FAIL'])
        error_tests = len([t for t in self.test_results if t['status'] == 'ERROR'])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 40)
        
        for result in self.test_results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[result['status']]
            print(f"{status_icon} {result['test']} ({result['duration']}s)")
            if result['status'] == 'ERROR':
                print(f"    Error: {result.get('error', 'Unknown error')}")
        
        # Save detailed report
        with open('test_report.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: test_report.json")
        print(f"📄 Logs saved to: test_results.log")
        
        return passed_tests == total_tests
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Hotel Booking Agent Tests")
        print("=" * 60)
        
        # Core functionality tests
        self.run_test("Database Connection", self.test_database_connection)
        self.run_test("AI Client Initialization", self.test_ai_client_initialization)
        self.run_test("Hotel Data Loading", self.test_hotel_data_loading)
        
        # AI functionality tests
        self.run_test("Intent Extraction", self.test_intent_extraction)
        self.run_test("Booking Info Extraction", self.test_booking_info_extraction)
        
        # Conversation flow tests
        self.run_test("Greeting Flow", self.test_conversation_flow_greeting)
        self.run_test("Inquiry Flow", self.test_conversation_flow_inquiry)
        self.run_test("Complete Booking Flow", self.test_booking_flow_complete)
        
        # Database tests
        self.run_test("Database Operations", self.test_database_operations)
        
        # Instagram integration tests
        self.run_test("Instagram Client Setup", self.test_instagram_client_setup)
        self.run_test("Webhook Parsing", self.test_webhook_parsing)
        
        # Error handling tests
        self.run_test("Error Handling", self.test_error_handling)
        
        # Integration test
        self.run_test("Integration Test", self.run_integration_test)
        
        # Generate report
        success = self.generate_test_report()
        
        # Cleanup
        self.cleanup_test_data()
        
        if success:
            print("\n🎉 All tests passed! Your hotel booking agent is ready for Instagram integration!")
            print("\nNext steps:")
            print("1. Set up Instagram Business account")
            print("2. Configure webhook URL")
            print("3. Set Instagram API credentials in .env")
            print("4. Deploy to production server")
        else:
            print("\n⚠️ Some tests failed. Please review the report and fix issues before proceeding.")
        
        return success

def main():
    """Main test execution"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Hotel Booking Agent Test Script")
        print("Usage: python test.py [--help]")
        print("\nThis script tests all components of the hotel booking agent.")
        print("Make sure you have:")
        print("1. Set up .env file with GEMINI_API_KEY")
        print("2. Installed all requirements: pip install -r requirements.txt")
        print("3. All project files in correct directory structure")
        return
    
    # Check environment
    if not os.path.exists('.env'):
        print("⚠️ Warning: .env file not found. Some tests may fail.")
        print("Create .env file with GEMINI_API_KEY for full testing.")
        input("Press Enter to continue anyway...")
    
    # Run tests
    tester = HotelAgentTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()