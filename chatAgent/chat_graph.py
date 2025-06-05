from langgraph.graph import StateGraph, END
from functools import partial
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from .chat_state import ChatAgentState
from .chat_nodes import get_philosopher_response_node_logic, load_initial_chat_state_node_logic
from .chat_llm_services import get_chat_llm

# Node names
LOAD_INITIAL_STATE = "load_initial_chat_state"
GET_RESPONSE = "get_philosopher_response"
USER_INPUT_NODE = "user_input_node" 

def should_continue_chat(state: ChatAgentState) -> str:
    """
    Determines if the chat should continue or end.
    For now, we'll always continue until the user explicitly quits in main_chat.py.
    This could be expanded (e.g., if state['current_user_input'].lower() in ['quit', 'exit']).
    """
    if state.get("error_message") and "LLM is not initialized" in state["error_message"]:
        print("[GRAPH] Critical error: LLM not initialized. Ending chat graph.")
        return END 
    return GET_RESPONSE 

def compile_chat_workflow(philosopher_name: str, roleplay_prompt: str):
    """
    Compiles and returns the LangGraph workflow for the chat agent.
    The graph will load initial state, then be ready to get responses.
    The chat loop (getting user input and re-invoking) is managed externally by main.py.
    """
    llm = get_chat_llm() 

    if not llm:
        print("[GRAPH ERROR] LLM could not be initialized. Chat workflow cannot be compiled.")
        return None

    conn = sqlite3.connect("chat_checkpoints.sqlite", check_same_thread=False)
    memory_saver = SqliteSaver(conn)
    workflow = StateGraph(ChatAgentState)

    bound_get_philosopher_response_node = partial(get_philosopher_response_node_logic, llm=llm)

    bound_load_initial_state_node = partial(load_initial_chat_state_node_logic, 
                                            philosopher_name=philosopher_name, 
                                            roleplay_prompt=roleplay_prompt)

    workflow.add_node(LOAD_INITIAL_STATE, bound_load_initial_state_node)
    workflow.add_node(GET_RESPONSE, bound_get_philosopher_response_node)
    
    workflow.set_entry_point(LOAD_INITIAL_STATE)

    workflow.add_edge(LOAD_INITIAL_STATE, GET_RESPONSE)
    
    workflow.add_edge(GET_RESPONSE, END) 
    
    app = workflow.compile(checkpointer=memory_saver)
    print("[GRAPH] Chat workflow compiled successfully with LOAD_INITIAL_STATE -> GET_RESPONSE -> END flow and SQLite checkpointer.")
    return app 