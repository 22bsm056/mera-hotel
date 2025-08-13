from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from agents.graph_builder import HotelGraphBuilder
from agents.hotel_agent import HotelAgent
from integrations.instagram_client import InstagramClient
from config import Config
import logging
import sys
import argparse
import streamlit as st

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
agent = HotelAgent()
graph_builder = HotelGraphBuilder(agent=agent)
instagram_client = InstagramClient()

def run_streamlit():
    """Run the Streamlit chat interface."""
    st.set_page_config(page_title="Hotel Booking AI Agent", page_icon="🏨", layout="centered")
    st.title("🏨 Hotel Booking AI Agent")
    st.write("Chat with the AI to book hotels or get hotel info.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_id" not in st.session_state:
        st.session_state.user_id = "streamlit_user"

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box for new message
    user_input = st.chat_input("Type your message...")
    if user_input:
        # Append user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get response from agent
        try:
            response = graph_builder.process(st.session_state.user_id, user_input)
        except Exception as e:
            response = f"⚠️ Error: {str(e)}"

        # Append agent response
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

def run_server():
    """Run the FastAPI server."""
    app = FastAPI(title="Hotel Booking AI Agent", version="1.0.0")

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "Hotel Booking AI Agent is running!", "status": "healthy"}

    @app.get("/webhook")
    async def verify_webhook(request: Request):
        params = request.query_params
        verify_token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        
        verified_challenge = instagram_client.verify_webhook(verify_token, challenge)
        if verified_challenge:
            logger.info("Webhook verified successfully")
            return int(verified_challenge)
        else:
            logger.error("Webhook verification failed")
            raise HTTPException(status_code=403, detail="Verification failed")

    @app.post("/webhook")
    async def handle_webhook(request: Request):
        try:
            webhook_data = await request.json()
            logger.info(f"Received webhook data: {webhook_data}")
            
            message_data = instagram_client.parse_webhook_message(webhook_data)
            if not message_data:
                return {"status": "no_message"}
            
            sender_id = message_data["sender_id"]
            message_text = message_data["message_text"]
            
            logger.info(f"Processing message from {sender_id}: {message_text}")
            response = graph_builder.process(sender_id, message_text)
            success = instagram_client.send_message(sender_id, response)
            
            if success:
                logger.info(f"Response sent successfully to {sender_id}")
                return {"status": "success", "response": response}
            else:
                logger.error(f"Failed to send response to {sender_id}")
                return {"status": "error", "message": "Failed to send response"}
                
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {"status": "error", "message": str(e)}

    @app.post("/chat")
    async def chat_endpoint(request: Request):
        try:
            data = await request.json()
            user_id = data.get("user_id", "test_user")
            message = data.get("message", "")
            
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            
            response = graph_builder.process(user_id, message)
            
            return {
                "user_id": user_id,
                "message": message,
                "response": response,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/bookings/{user_id}")
    async def get_user_bookings(user_id: str):
        try:
            bookings = graph_builder.agent.db.get_user_bookings(user_id)
            return {
                "user_id": user_id,
                "bookings": [booking.to_dict() for booking in bookings],
                "count": len(bookings)
            }
        except Exception as e:
            logger.error(f"Error getting bookings: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/booking/{booking_id}")
    async def get_booking(booking_id: str):
        try:
            booking = graph_builder.agent.db.get_booking(booking_id)
            if booking:
                return booking.to_dict()
            else:
                raise HTTPException(status_code=404, detail="Booking not found")
        except Exception as e:
            logger.error(f"Error getting booking: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/hotel-info")
    async def get_hotel_info():
        return graph_builder.agent.hotel_info

    logger.info("Starting Hotel Booking AI Agent server...")
    logger.info(f"Hotel: {Config.HOTEL_NAME}")
    
    if not Config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in environment variables")
        sys.exit(1)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

def main():
    parser = argparse.ArgumentParser(description="Hotel Booking AI Agent")
    parser.add_argument(
        '--mode',
        choices=['streamlit', 'server'],
        default='streamlit',
        help='Run mode: streamlit for chat UI, server for FastAPI API'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'streamlit':
        run_streamlit()
    else:
        run_server()

if __name__ == "__main__":
    main()
