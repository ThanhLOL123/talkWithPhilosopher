from typing import Dict, Any
from langgraph.graph import StateGraph, END

from .state import PhilosopherResearchState
from .llm_services import get_default_llm
from .tool_services import get_default_search_tool
from .nodes import (
    load_initial_state_node_logic,
    select_next_category_node_logic,
    generate_queries_for_category_node_logic,
    tavily_search_for_category_node_logic,
    extract_information_for_category_node_logic,
    accumulate_and_increment_category_node_logic,
    synthesize_final_profile_node_logic
)


def load_initial_state_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    philosopher_name = state.get("philosopher_name")
    if not philosopher_name:
        print("[ERROR][Graph] philosopher_name is missing from initial state.")
        return {"error_messages": state.get("error_messages", []) + ["Missing philosopher_name for graph input"]}
    print(f"[GRAPH] Calling: load_initial_state_node_logic for {philosopher_name}")
    return load_initial_state_node_logic(philosopher_name)


def select_next_category_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print("[GRAPH] Calling: select_next_category_node_logic")
    return select_next_category_node_logic(state)


def generate_queries_for_category_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print(f"[GRAPH] Calling: generate_queries_for_category_node_logic for category: {state.get('current_category_name')}")
    try:
        llm = get_default_llm()
        return generate_queries_for_category_node_logic(state, llm)
    except Exception as e:
        error_msg = f"LLM init error in generate_queries_for_category_node: {str(e)}"
        print(f"[ERROR][Graph] {error_msg}")
        return {"error_messages": state.get("error_messages", []) + [error_msg]}


def tavily_search_for_category_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print(f"[GRAPH] Calling: tavily_search_for_category_node_logic for category: {state.get('current_category_name')}")
    try:
        tavily_tool = get_default_search_tool()
        return tavily_search_for_category_node_logic(state, tavily_tool)
    except Exception as e:
        error_msg = f"Search tool init error in tavily_search_for_category_node: {str(e)}"
        print(f"[ERROR][Graph] {error_msg}")
        return {"error_messages": state.get("error_messages", []) + [error_msg]}


def extract_information_for_category_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print(f"[GRAPH] Calling: extract_information_for_category_node_logic for category: {state.get('current_category_name')}")
    try:
        llm = get_default_llm()
        return extract_information_for_category_node_logic(state, llm)
    except Exception as e:
        error_msg = f"LLM/extraction error in extract_information_for_category_node: {str(e)}"
        print(f"[ERROR][Graph] {error_msg}")
        return {"error_messages": state.get("error_messages", []) + [error_msg]}


def accumulate_and_increment_category_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print(f"[GRAPH] Calling: accumulate_and_increment_category_node_logic for category: {state.get('current_category_name')}")
    return accumulate_and_increment_category_node_logic(state)


def synthesize_final_profile_node(state: PhilosopherResearchState) -> Dict[str, Any]:
    print("[GRAPH] Calling: synthesize_final_profile_node_logic")
    try:
        llm = get_default_llm()
        return synthesize_final_profile_node_logic(state, llm)
    except Exception as e:
        error_msg = f"LLM/synthesis error in synthesize_final_profile_node: {str(e)}"
        print(f"[ERROR][Graph] {error_msg}")
        return {"final_synthesized_profile": None, "error_messages": state.get("error_messages", []) + [error_msg]}



def should_continue_category_loop(state: PhilosopherResearchState) -> str:
    if state.get("current_category_name") is not None:
        print("[GRAPH] Condition: Continue category loop.")
        return "generate_queries_for_category"
    else:
        print("[GRAPH] Condition: Category loop finished. Proceed to synthesis.")
        return "synthesize_final_profile"


def compile_sequential_research_graph() -> StateGraph:
    workflow = StateGraph(PhilosopherResearchState)
    
    workflow.add_node("load_initial_state", load_initial_state_node)
    workflow.add_node("select_next_category", select_next_category_node)
    workflow.add_node("generate_queries_for_category", generate_queries_for_category_node)
    workflow.add_node("tavily_search_for_category", tavily_search_for_category_node)
    workflow.add_node("extract_information_for_category", extract_information_for_category_node)
    workflow.add_node("accumulate_and_increment_category", accumulate_and_increment_category_node)
    workflow.add_node("synthesize_final_profile", synthesize_final_profile_node)
    
    workflow.set_entry_point("load_initial_state")
    workflow.add_edge("load_initial_state", "select_next_category")
    
    workflow.add_conditional_edges(
        "select_next_category",
        should_continue_category_loop,
        {
            "generate_queries_for_category": "generate_queries_for_category",
            "synthesize_final_profile": "synthesize_final_profile"      
        }
    )
    
    workflow.add_edge("generate_queries_for_category", "tavily_search_for_category")
    workflow.add_edge("tavily_search_for_category", "extract_information_for_category")
    workflow.add_edge("extract_information_for_category", "accumulate_and_increment_category")
    workflow.add_edge("accumulate_and_increment_category", "select_next_category") 
    
    workflow.add_edge("synthesize_final_profile", END)
    
    return workflow.compile()


def get_default_research_graph() -> StateGraph:
    print("[INFO] Compiling SEQUENTIAL research graph.")
    return compile_sequential_research_graph()
