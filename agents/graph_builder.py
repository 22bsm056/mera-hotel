from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
import operator
from models.booking_models import ConversationState
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: Annotated[List[str], operator.add]
    user_id: str
    current_intent: str
    booking_data: Dict[str, Any]
    next_action: str

class HotelGraphBuilder:
    def __init__(self, agent):
        self.agent = agent
        self.workflow = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("process_message", self._process_message_node)
        workflow.add_node("handle_booking", self._handle_booking_node)
        workflow.add_node("handle_reschedule", self._handle_reschedule_node)
        workflow.add_node("handle_inquiry", self._handle_inquiry_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        workflow.set_entry_point("process_message")
        
        workflow.add_conditional_edges(
            "process_message",
            self._route_intent,
            {
                "booking": "handle_booking",
                "reschedule": "handle_reschedule", 
                "inquiry": "handle_inquiry",
                "cancel": "handle_inquiry",
                "greeting": "handle_inquiry",
                "response": "generate_response"
            }
        )
        
        workflow.add_edge("handle_booking", "generate_response")
        workflow.add_edge("handle_reschedule", "generate_response")
        workflow.add_edge("handle_inquiry", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _process_message_node(self, state: AgentState) -> dict:
        if not state["messages"]:
            return {"current_intent": "inquiry", "next_action": "inquiry"}
            
        last_message = state["messages"][-1]
        intent = self.agent.ai.extract_intent(last_message)
        return {
            "current_intent": intent,
            "next_action": intent
        }
    
    def _handle_booking_node(self, state: AgentState) -> dict:
        try:
            response = self.agent.process_message(state["user_id"], state["messages"][-1])
            return {"messages": [response], "next_action": "response"}
        except Exception as e:
            logger.error(f"Error in booking node: {e}")
            return {"messages": ["I encountered an error processing your booking. Please try again."], "next_action": "response"}
    
    def _handle_reschedule_node(self, state: AgentState) -> dict:
        try:
            response = self.agent.process_message(state["user_id"], state["messages"][-1])
            return {"messages": [response], "next_action": "response"}
        except Exception as e:
            logger.error(f"Error in reschedule node: {e}")
            return {"messages": ["I encountered an error processing your reschedule request. Please try again."], "next_action": "response"}
    
    def _handle_inquiry_node(self, state: AgentState) -> dict:
        try:
            response = self.agent.process_message(state["user_id"], state["messages"][-1])
            return {"messages": [response], "next_action": "response"}
        except Exception as e:
            logger.error(f"Error in inquiry node: {e}")
            return {"messages": ["I'm here to help! Please let me know what you need assistance with."], "next_action": "response"}
    
    def _generate_response_node(self, state: AgentState) -> dict:
        return {"next_action": "complete"}
    
    def _route_intent(self, state: AgentState) -> str:
        intent = state.get("current_intent", "inquiry")
        valid_intents = ["booking", "reschedule", "inquiry", "cancel", "greeting"]
        return intent if intent in valid_intents else "inquiry"
    
    def process(self, user_id: str, message: str) -> str:
        try:
            if not user_id or not message:
                return "I didn't receive your message properly. Please try again."
            
            result = self.workflow.invoke({
                "messages": [message],
                "user_id": user_id,
                "current_intent": "",
                "booking_data": {},
                "next_action": ""
            })
            
            if result.get("messages") and len(result["messages"]) > 0:
                return result["messages"][-1]
            else:
                return self.agent.process_message(user_id, message)
                
        except Exception as e:
            logger.error(f"Graph processing error: {e}")
            return self.agent.process_message(user_id, message)