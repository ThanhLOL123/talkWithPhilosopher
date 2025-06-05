import importlib.util
import os

DEFAULT_PROMPT = "You are a helpful AI assistant. Please answer the user's questions thoughtfully."
DEFAULT_PHILOSOPHER_NAME = "Default Philosopher"

def load_roleplay_prompt_and_name(prompt_file_path: str = "prompt.py") -> tuple[str, str]:

    roleplay_prompt = DEFAULT_PROMPT
    philosopher_name = DEFAULT_PHILOSOPHER_NAME

    if not os.path.exists(prompt_file_path):
        print(f"[PROMPT LOADER WARNING] Prompt file '{prompt_file_path}' not found. Using default prompt.")
        return roleplay_prompt, philosopher_name

    try:
        spec = importlib.util.spec_from_file_location("generated_prompt_module", prompt_file_path)
        if spec and spec.loader:
            prompt_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(prompt_module)
            
            if hasattr(prompt_module, "generated_prompt") and isinstance(prompt_module.generated_prompt, str):
                roleplay_prompt = prompt_module.generated_prompt
                print(f"[PROMPT LOADER] Successfully loaded roleplay prompt from '{prompt_file_path}'.")
                
                try:
                    with open(prompt_file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines:
                            if "# Tệp prompt được tạo tự động cho" in line or "# Auto-generated prompt file for" in line:
                                name_part = line.split("cho")[-1].strip() if "cho" in line else line.split("for")[-1].strip()
                                if name_part:
                                    philosopher_name = name_part
                                    print(f"[PROMPT LOADER] Extracted philosopher name: {philosopher_name}")
                                    break
                except Exception as e:
                    print(f"[PROMPT LOADER WARNING] Could not extract philosopher name from comments in '{prompt_file_path}': {e}")
            else:
                print(f"[PROMPT LOADER WARNING] 'generated_prompt' variable not found or not a string in '{prompt_file_path}'. Using default prompt.")
        else:
            print(f"[PROMPT LOADER ERROR] Could not load spec for prompt file '{prompt_file_path}'. Using default prompt.")

    except Exception as e:
        print(f"[PROMPT LOADER ERROR] Failed to load prompt from '{prompt_file_path}': {e}. Using default prompt.")
    
    if not philosopher_name or philosopher_name == DEFAULT_PHILOSOPHER_NAME:
        if "Karl Marx" in roleplay_prompt: 
            philosopher_name = "Karl Marx"
        elif "Socrates" in roleplay_prompt: 
             philosopher_name = "Socrates"

    return roleplay_prompt, philosopher_name

if __name__ == '__main__':
    prompt, name = load_roleplay_prompt_and_name()
    print(f"\n--- Loaded Prompt for: {name} ---")
    print(prompt[:500] + "...")

    prompt_not_exist, name_not_exist = load_roleplay_prompt_and_name("non_existent_prompt.py")
    print(f"\n--- Test Non-Existent Prompt for: {name_not_exist} ---")
    print(prompt_not_exist[:500] + "...") 