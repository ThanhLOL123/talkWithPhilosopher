import subprocess
import sys
import os
import uuid
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from .chat_prompt_loader import load_roleplay_prompt_and_name
from .chat_graph import compile_chat_workflow

CWD = os.path.dirname(os.path.realpath(__file__))
WORKSPACE_ROOT = os.path.dirname(CWD) 
if WORKSPACE_ROOT not in sys.path:
    sys.path.append(WORKSPACE_ROOT)


def run_process_information_script(script_path: str = "chatAgent/processInformation.py") -> bool:
    """
    Runs the processInformation.py script to generate/update prompt.py.
    Returns True if successful, False otherwise.
    """
    absolute_script_path = os.path.join(WORKSPACE_ROOT, script_path) 

    if not os.path.exists(absolute_script_path):
        relative_script_path = os.path.join(os.path.dirname(__file__), "processInformation.py")
        if os.path.exists(relative_script_path):
            absolute_script_path = relative_script_path
        else:
            print(f"[MAIN CHAT ERROR] processInformation.py script not found at {absolute_script_path} or {relative_script_path}.")
            print("Please ensure the script exists and the path is correct.")
            return False

    try:
        print(f"[MAIN CHAT] Running {absolute_script_path} to generate roleplaying prompt... pathogenic agent") 

        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([python_path, WORKSPACE_ROOT]) if python_path else WORKSPACE_ROOT
        
        process = subprocess.Popen([sys.executable, absolute_script_path], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   cwd=WORKSPACE_ROOT, 
                                   env=env)
        stdout, stderr = process.communicate(timeout=120) 
        
        print("--- Output from processInformation.py ---")
        if stdout:
            print(stdout)
        if stderr:
            print("Stderr:", stderr, file=sys.stderr)
        print("--- End of output from processInformation.py ---")

        if process.returncode != 0:
            print(f"[MAIN CHAT ERROR] {absolute_script_path} failed with return code {process.returncode}.")
            return False
        print(f"[MAIN CHAT] {absolute_script_path} completed successfully.")
        return True
    except subprocess.TimeoutExpired:
        print(f"[MAIN CHAT ERROR] {absolute_script_path} timed out after 120 seconds.")
        process.kill()
        stdout, stderr = process.communicate()
        if stdout: print(stdout)
        if stderr: print("Stderr:", stderr, file=sys.stderr)
        return False
    except Exception as e:
        print(f"[MAIN CHAT ERROR] Failed to run {absolute_script_path}: {e}")
        return False

def main_chat_loop():
    """
    Main loop for the philosopher chat agent.
    """
    load_dotenv(os.path.join(WORKSPACE_ROOT, ".env")) 
    prompt_file_relative_to_chat_agent = "prompt.py"
    absolute_prompt_file_path = os.path.join(os.path.dirname(__file__), prompt_file_relative_to_chat_agent)

    if not run_process_information_script():
        print("[MAIN CHAT] Exiting due to failure in prompt generation script.")
    roleplay_prompt, philosopher_name = load_roleplay_prompt_and_name(absolute_prompt_file_path)

    if "Default Philosopher" in philosopher_name and "default prompt" not in roleplay_prompt.lower():
        print(f"[MAIN CHAT WARNING] Loaded prompt for '{philosopher_name}' but it might be the default. The roleplay might not be specific.")
    elif "Default Philosopher" in philosopher_name:
        print("[MAIN CHAT CRITICAL] Could not load specific philosopher prompt. Exiting chat agent.")
        return

    chat_workflow = compile_chat_workflow(philosopher_name, roleplay_prompt)

    if not chat_workflow:
        print("[MAIN CHAT CRITICAL] Failed to compile chat workflow. Most likely LLM initialization failed. Exiting.")
        return
    
    # Generate a unique session ID for this chat
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"[MAIN CHAT] Starting new chat session with ID: {thread_id}")

    # current_graph_state = {"current_user_input": ""} 
    try:
        # For the first interaction in a new session, current_user_input can be empty 
        # as LOAD_INITIAL_STATE is expected to provide an initial greeting.
        initial_input_for_setup = {"current_user_input": ""} # Can be an empty string or a conventional first user message
        initial_setup_response = chat_workflow.invoke(initial_input_for_setup, config)
        
        chat_history_from_init = initial_setup_response.get("chat_history", [])
        
        # Display the initial greeting from the AIMessage in chat_history_from_init
        if chat_history_from_init and isinstance(chat_history_from_init[-1], AIMessage):
            print(f"\n{philosopher_name}: {chat_history_from_init[-1].content}")
        elif not chat_history_from_init: # Fallback if no greeting was added for some reason
            print(f"\nGreetings! You are now conversing with {philosopher_name}.")
            
        print("Type 'quit', 'exit', or 'bye' to end the conversation.")

    except Exception as e:
        print(f"[MAIN CHAT ERROR] Error during initial graph invocation: {e}")
        print("Exiting chat.")
        return

    # 5. Chat loop
    while True:
        try:
            user_input = input(f"\nAsk {philosopher_name}: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"\n{philosopher_name}: Farewell! It was enlightening.")
                break

            
            invocation_input = {"current_user_input": user_input}
            
            print(f"\n{philosopher_name} is thinking...")

            response_state = chat_workflow.invoke(invocation_input, config) # Pass config here

            if response_state:
                final_chat_history = response_state.get("chat_history", [])
                if final_chat_history:
                    ai_message = final_chat_history[-1]
                    if isinstance(ai_message, AIMessage):
                        print(f"\n{philosopher_name}: {ai_message.content}")
                    else:
                        print(f"[MAIN CHAT DEBUG] Unexpected last message type: {type(ai_message)}") 
                
                if response_state.get("error_message"):
                    print(f"[MAIN CHAT NOTE] An error occurred in the last turn: {response_state['error_message']}")
            else:
                print("[MAIN CHAT WARNING] Received no response state from the graph.")

        except KeyboardInterrupt:
            print(f"\n{philosopher_name}: It seems our time is up. Farewell!")
            break
        except Exception as e:
            print(f"[MAIN CHAT ERROR] An unexpected error occurred: {e}")


if __name__ == "__main__":
    main_chat_loop() 