"""
Main Streamlit Application Entry Point.

This application integrates:
1. The Deep Researcher Agent to generate comprehensive philosopher profiles.
2. A Chat Agent (to be fully implemented) to converse with the researched philosopher.
"""

import streamlit as st
import os
import json
import sys
import uuid # Added for thread_id generation
from dotenv import load_dotenv
import asyncio # For running async functions from processInformation
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# Ensure correct paths for imports - assuming main.py is in the workspace root
CWD_MAIN = os.path.dirname(os.path.realpath(__file__))
if CWD_MAIN not in sys.path:
    sys.path.append(CWD_MAIN)

# Attempt to import agent components
try:
    from research_agent.graph import get_default_research_graph
    from research_agent.state import PhilosopherResearchState
    # For Chat Agent (will be used later)
    from chatAgent.chat_prompt_loader import load_roleplay_prompt_and_name
    from chatAgent.chat_graph import compile_chat_workflow
    from chatAgent.processInformation import generate_roleplay_prompt_from_json_string # Import the refactored function
    from chatAgent.chat_llm_services import get_chat_llm # For chat agent's main LLM and intro LLM
except ImportError as e:
    st.error(f"Error importing agent components: {e}. Please ensure all modules are in the correct paths and dependencies are installed. CWD: {CWD_MAIN}, sys.path: {sys.path}")
    st.stop()

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Philosopher AI Agents",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Global State Management (using Streamlit session state) ---
def init_session_state():
    if "philosopher_name" not in st.session_state:
        st.session_state.philosopher_name = ""
    if "research_results" not in st.session_state:
        st.session_state.research_results = None
    if "research_running" not in st.session_state:
        st.session_state.research_running = False
    if "chat_initialized" not in st.session_state:
        st.session_state.chat_initialized = False
    if "chat_workflow" not in st.session_state:
        st.session_state.chat_workflow = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [] # Stores AIMessage, HumanMessage
    if "roleplay_prompt" not in st.session_state:
        st.session_state.roleplay_prompt = ""
    if "chat_philosopher_name" not in st.session_state:
        st.session_state.chat_philosopher_name = ""
    if "chat_thread_id" not in st.session_state:
        st.session_state.chat_thread_id = None

init_session_state()

# --- Environment Loading --- 
def load_environment_streamlit():
    load_dotenv(os.path.join(CWD_MAIN, ".env"))
    required_vars = ["GROQ_API_KEY", "TAVILY_API_KEY"] # OPENROUTER_API_KEY might not be needed if Groq is primary
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        st.error(f"Missing environment variables: {', '.join(missing_vars)}. Please check your .env file.")
        return False
    return True

# --- Deep Research Agent Functions --- 
def run_deep_research(philosopher_name: str):
    st.session_state.research_running = True
    st.session_state.research_results = None
    st.session_state.philosopher_name = philosopher_name
    
    initial_input = {"philosopher_name": philosopher_name}
    graph = get_default_research_graph()

    if not graph:
        st.error("Failed to initialize the research graph. Check LLM service configuration.")
        st.session_state.research_running = False
        return

    with st.status(f"🚀 Researching {philosopher_name}... This may take a few minutes.", expanded=True) as status_ui:
        try:
            st.write("Step 1: Initializing Research Agent...")
            # Note: Actual graph execution is blocking. For true async updates in Streamlit,
            # this would need a more complex setup (e.g., websockets, background tasks).
            # For now, st.status provides a good UX for synchronous long operations.
            final_state = graph.invoke(initial_input, {"recursion_limit": 120}) # Default: 25, needs more for 8 categories
            st.session_state.research_results = final_state
            status_ui.update(label=f"✅ Research complete for {philosopher_name}!", state="complete", expanded=False)
        except Exception as e:
            st.error(f"An error occurred during research: {e}")
            status_ui.update(label=f"❌ Research failed for {philosopher_name}.", state="error", expanded=True)
            st.session_state.research_results = {"error": str(e)}
        finally:
            st.session_state.research_running = False

def display_research_results(results: PhilosopherResearchState):
    if not results:
        return

    st.subheader(f"📊 Research Results for {results.get('philosopher_name', 'N/A')}")

    if results.get("error"):
        st.error(f"Research Error: {results.get('error')}")
        return
    
    if results.get("error_messages"):
        st.warning("Errors encountered during research:")
        for error in results.get("error_messages", []):
            st.text(f"- {error}")

    st.markdown(f"**📈 Statistics:**")
    st.text(f"  - Total Queries Generated: {results.get('total_generated_queries_count', 0)}")
    st.text(f"  - Total Search Results: {results.get('total_search_results_count', 0)}")
    accumulated_info = results.get('accumulated_extracted_information', {})
    total_extracted_items = sum(len(v) for v in accumulated_info.values()) if isinstance(accumulated_info, dict) else 0
    st.text(f"  - Total Extracted Information Items: {total_extracted_items}")

    profile = results.get("final_synthesized_profile")
    if profile and not profile.get("error"):        
        st.markdown("**📚 Synthesized Philosopher Profile:**")
        category_order = [
            "Biographical_Historical_Context", "Major_Works_Core_Content",
            "Core_Philosophical_Doctrines_Ideas", "Views_on_Specific_Philosophical_Topics",
            "Philosophical_Relationships_Interactions", "Critiques_Evaluations_of_Doctrines",
            "Characteristic_Philosophical_Methodology", "Argumentative_Style_Rhetoric",
            "_final_synthesis_metadata"
        ]
        for category_key in category_order:
            if category_key in profile:
                with st.expander(f"{category_key.replace('_', ' ').title()}", expanded=False):
                    st.json(profile[category_key])
        
        # Offer download for the full JSON research result
        results_json_string = json.dumps(results, ensure_ascii=False, indent=2)
        clean_name = "".join(c for c in results.get("philosopher_name", "philosopher") if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_').lower()
        st.download_button(
            label=f"💾 Download Full Research for {results.get('philosopher_name', 'Philosopher')}",
            data=results_json_string,
            file_name=f"research_{clean_name}.json",
            mime="application/json"
        )
    elif profile and profile.get("error"):
        st.error(f"Error during profile synthesis: {profile.get('error')}")
    else:
        st.warning("No synthesized profile available or profile generation failed.")

# --- Chat Agent Functions (Placeholder for now, will be expanded) ---
async def initialize_chat_agent_streamlit(research_data_json_str: str):
    st.session_state.chat_initialized = False
    st.session_state.chat_workflow = None
    st.session_state.chat_history = []
    st.session_state.roleplay_prompt = ""
    st.session_state.chat_philosopher_name = ""
    st.session_state.chat_thread_id = None

    intro_llm = get_chat_llm() # Uses chat_llm_services, ensure GROQ_API_KEY is set
    if not intro_llm:
        st.error("Failed to initialize LLM for generating chat introduction. Cannot start chat.")
        return

    # Generate the roleplay prompt using the imported function
    # This now happens directly, not via subprocess.
    prompt_string, philosopher_name = await generate_roleplay_prompt_from_json_string(research_data_json_str, intro_llm)

    if not prompt_string or "Lỗi" in prompt_string: # Basic error check
        st.error(f"Failed to generate roleplaying prompt: {prompt_string}")
        return
    
    st.session_state.roleplay_prompt = prompt_string
    st.session_state.chat_philosopher_name = philosopher_name if philosopher_name else "Philosopher"
    
    chat_workflow_instance = compile_chat_workflow(st.session_state.chat_philosopher_name, st.session_state.roleplay_prompt)
    if not chat_workflow_instance:
        st.error("Failed to compile chat workflow. LLM for chat might be missing or misconfigured.")
        return
    
    st.session_state.chat_workflow = chat_workflow_instance
    st.session_state.chat_initialized = True
    
    # Generate a unique thread_id for this chat session
    st.session_state.chat_thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": st.session_state.chat_thread_id}}
    st.info(f"Chat Session ID: {st.session_state.chat_thread_id}") # For debugging/visibility

    # Initial invocation to set up the graph state
    try:
        initial_chat_state = {"current_user_input": ""} 
        setup_response = st.session_state.chat_workflow.invoke(initial_chat_state, config) # Pass config
        
        st.session_state.chat_history = setup_response.get("chat_history", [])

        st.success(f"Chat agent for {st.session_state.chat_philosopher_name} initialized!")
    except Exception as e:
        st.error(f"Error during chat agent initial graph invocation: {e}")
        st.session_state.chat_initialized = False

def display_chat_interface():
    st.subheader(f"💬 Chat with {st.session_state.get('chat_philosopher_name', 'Philosopher')}")

    if not st.session_state.get("chat_initialized") or not st.session_state.get("chat_workflow"):
        st.warning("Chat agent is not initialized. Please research a philosopher and start the chat agent first.")
        uploaded_file = st.file_uploader("Or upload a research JSON file to start chat:", type=["json"], key="chat_json_upload")
        if uploaded_file is not None:
            json_str_content = uploaded_file.getvalue().decode("utf-8")
            # Use asyncio.run for the async function in Streamlit context
            asyncio.run(initialize_chat_agent_streamlit(json_str_content))
            st.rerun() # Rerun to reflect initialized state
        return

    # Display chat messages from history
    for message in st.session_state.get("chat_history", []):
        avatar = "🧑‍🏫" if message.type == "ai" else "👤"
        with st.chat_message(message.type, avatar=avatar):
            st.markdown(message.content)
    
    user_input = st.chat_input(f"Ask {st.session_state.chat_philosopher_name}...")

    if user_input:
        st.session_state.chat_history.append(HumanMessage(content=user_input))
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        
        with st.spinner(f"{st.session_state.chat_philosopher_name} is thinking..."):
            try:
                invocation_input = {"current_user_input": user_input, "chat_history": st.session_state.chat_history[:-1]} 
                
                # Ensure thread_id is available for the config
                if not st.session_state.get("chat_thread_id"):
                    st.error("CRITICAL: Chat session ID (thread_id) is missing. Cannot continue securely.")
                    # Potentially re-initialize or halt, for now, we'll just error and try to prevent invocation without it.
                    return 
                
                config = {"configurable": {"thread_id": st.session_state.chat_thread_id}}
                response_state = st.session_state.chat_workflow.invoke(invocation_input, config) # Pass config
                
                ai_response_content = "I seem to be at a loss for words."
                if response_state and response_state.get("chat_history"):
                    # The full history is returned, new AI message is the last one
                    new_ai_message = response_state["chat_history"][-1]
                    if new_ai_message.type == "ai":
                        ai_response_content = new_ai_message.content
                    st.session_state.chat_history = response_state["chat_history"]
                else: # Fallback if history structure isn't as expected
                    st.session_state.chat_history.append(AIMessage(content=ai_response_content))

                if response_state and response_state.get("error_message"):
                    st.error(f"Chat Error: {response_state.get('error_message')}")

            except Exception as e:
                st.error(f"Error during chat: {e}")
                ai_response_content = "I encountered an issue and cannot respond right now."
                st.session_state.chat_history.append(AIMessage(content=ai_response_content))
        st.rerun() # Rerun to display the new messages

# --- Main Streamlit App Layout --- 
st.title("🧠 Philosopher AI Agents Portal")

if not load_environment_streamlit():
    st.stop()

# Create tabs for different agents
agent_tab1, agent_tab2 = st.tabs(["🔍 Deep Research Agent", "💬 Chat With Philosopher"])

with agent_tab1:
    st.header("🔬 Conduct Deep Research on a Philosopher")
    
    # Use session state for philosopher name input to persist it
    name_input = st.text_input("Enter philosopher's name to research:", value=st.session_state.philosopher_name, key="research_name_input")
    
    if st.button("Start Research", key="start_research_button", disabled=st.session_state.research_running):
        if name_input:
            st.session_state.philosopher_name = name_input # Update session state from input box
            run_deep_research(st.session_state.philosopher_name)
        else:
            st.warning("Please enter a philosopher's name.")
    
    if st.session_state.research_running:
        st.info("Research is in progress... Please wait.")
        # Progress bar can be added here if graph streaming is implemented

    if st.session_state.research_results:
        display_research_results(st.session_state.research_results)
        # Add button to send results to chat agent
        if not st.session_state.research_results.get("error") and st.session_state.research_results.get("final_synthesized_profile"):
            if st.button("Start Chat with this Philosopher", key="start_chat_from_research"):
                json_str_content = json.dumps(st.session_state.research_results) # Pass the full research state
                # Use asyncio.run to call the async function in Streamlit
                asyncio.run(initialize_chat_agent_streamlit(json_str_content))
                st.success("Chat agent initialization started. Switch to the 'Chat With Philosopher' tab.")
                # Potentially switch tabs automatically if Streamlit supports it easily, or guide user.
                # For now, user needs to switch manually.

with agent_tab2:
    st.header("🗣️ Converse with a Researched Philosopher")
    display_chat_interface()

# Add a sidebar with information or global controls if needed
st.sidebar.header("About")
st.sidebar.info(
    "This application combines a Deep Research Agent to build philosopher profiles "
    "and a Chat Agent to interact with them. Powered by LangGraph and Groq."
)

if __name__ == "__main__":
    # Streamlit apps are typically run with `streamlit run main.py`
    # This __main__ block is mostly for completeness or if you ever try to run it as a script,
    # though that won't start the Streamlit server.
    print("To run this application, use the command: streamlit run main.py") 