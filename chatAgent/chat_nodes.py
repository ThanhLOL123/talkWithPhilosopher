from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq

from .chat_state import ChatAgentState

def get_philosopher_response_node_logic(state: ChatAgentState, llm: ChatGroq) -> Dict[str, Any]:
 
    print(f"[CHAT NODE] Getting response from {state['philosopher_name']}...")
    current_user_input = state["current_user_input"]
    chat_history = state.get("chat_history", [])
    roleplay_prompt_system_message = SystemMessage(content=state["roleplay_prompt"])
    
    messages_for_llm = [roleplay_prompt_system_message] + chat_history + [HumanMessage(content=current_user_input)]

    try:
        if not llm:
            print("[CHAT NODE ERROR] LLM not available. Returning error message.")
            ai_response_content = "I am unable to respond at this time. The language model is not configured."
            updated_chat_history = chat_history + [HumanMessage(content=current_user_input), AIMessage(content=ai_response_content)]
            return {
                "chat_history": updated_chat_history,
                "current_user_input": "",
                "error_message": "LLM is not initialized."
            }

        ai_response = llm.invoke(messages_for_llm)
        ai_response_content = ai_response.content
        
        updated_chat_history = chat_history + [HumanMessage(content=current_user_input), AIMessage(content=ai_response_content)]
        
        return {
            "chat_history": updated_chat_history,
            "current_user_input": "", 
            "error_message": None 
        }
    except Exception as e:
        error_msg = f"Error during LLM call in chat node: {str(e)}"
        print(f"[CHAT NODE ERROR] {error_msg}")
        ai_error_response = "I apologize, but I encountered an error trying to formulate my response."
        updated_chat_history = chat_history + [HumanMessage(content=current_user_input), AIMessage(content=ai_error_response)]
        return {
            "chat_history": updated_chat_history, 
            "current_user_input": "",
            "error_message": error_msg
        }

def load_initial_chat_state_node_logic(state: ChatAgentState, philosopher_name: str, roleplay_prompt: str) -> Dict[str, Any]:
    print(f"[CHAT NODE] Ensuring initial chat state for: {philosopher_name}")

    # The 'state' parameter here is the state potentially loaded by the checkpointer.
    # chat_history could already be populated.
    current_chat_history = state.get("chat_history", [])
    initial_greeting_message = f"I am {philosopher_name}. Ask me anything about my philosophy or life."

    # Add a greeting only if history is empty and doesn't already contain this specific greeting
    if not current_chat_history:
        print(f"[CHAT NODE] Chat history is empty for {philosopher_name}. Adding initial greeting.")
        current_chat_history = [AIMessage(content=initial_greeting_message)]
    elif current_chat_history and isinstance(current_chat_history[0], AIMessage) and current_chat_history[0].content == initial_greeting_message:
        # This check is to prevent adding duplicate greetings if this node runs multiple times at the start
        # for some reason, though with current graph flow it shouldn't.
        pass # Greeting already exists
    elif current_chat_history: # History exists but doesn't start with our specific greeting
         # This case indicates the history is already ongoing. Do not prepend a greeting.
        print(f"[CHAT NODE] Chat history is not empty for {philosopher_name}. Not adding initial greeting.")


    return {
        "philosopher_name": philosopher_name,
        "roleplay_prompt": roleplay_prompt,
        "chat_history": current_chat_history,
        "current_user_input": state.get("current_user_input", ""), # Preserve incoming user input
        "error_message": state.get("error_message") # Preserve existing error message or set to None if not present
    } 