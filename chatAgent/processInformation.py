import json
import asyncio # Cần thiết cho các hoạt động bất đồng bộ
import os
import sys # Added for sys.path modification
from typing import Dict, Any # Added Dict and Any
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage

# Ensure the chatAgent directory's parent is in the Python path for potential relative imports
# if this script is called from elsewhere (e.g., by the main Streamlit app)
CWD_PROCESS = os.path.dirname(os.path.realpath(__file__))
PROCESS_WORKSPACE_ROOT = os.path.dirname(CWD_PROCESS)
if PROCESS_WORKSPACE_ROOT not in sys.path:
    sys.path.append(PROCESS_WORKSPACE_ROOT)


async def generate_introductory_paragraph_llm(
    philosopher_name: str, 
    life_events: str, 
    era_context: str, 
    academic_environment: str,
    llm_instance: ChatGroq # Expect an initialized LLM instance
) -> str:
    if not llm_instance:
        print("[PROCESS_INFO_LLM] LLM instance not provided. Using fallback intro.")
        return (
            f"You are the philosopher named {philosopher_name}. You lived during: {era_context}.\n"
            f"Key Life Events: {life_events}\n"
            f"Academic Environment: {academic_environment}\n\n"
            f"Your objective is to answer questions and engage in discussions as {philosopher_name}, "
            "drawing upon the philosophical aspects, life events, and stylistic traits summarized below. "
            f"Aim to provide responses that are insightful, analytical, and authentically reflect the thinking of {philosopher_name}."
        )

    llm_instruction_content = (
        f"You are an AI assistant helping to create a roleplaying prompt. "
        f"The end user of the main prompt will be roleplaying as the philosopher: {philosopher_name}.\n\n"
        "Your task is to generate a single, concise, and engaging introductory paragraph **in English** for this roleplaying prompt. "
        "This paragraph should seamlessly integrate the following biographical details:\n"
        f"- Philosopher's Name: {philosopher_name}\n"
        f"- Key Life Events Summary: {life_events}\n"
        f"- Era Context: {era_context}\n"
        f"- Academic Environment: {academic_environment}\n\n"
        f"The paragraph MUST start with: 'You are the philosopher named {philosopher_name}. You lived during...'.\n"
        "After crafting this narrative introduction, on a NEW LINE, append the following standard roleplaying instructions verbatim (DO NOT MODIFY THIS PART):\n"
        f"'Your objective is to answer questions and engage in discussions as {philosopher_name}, "
        "drawing upon the philosophical aspects, life events, and stylistic traits summarized below. "
        f"Aim to provide responses that are insightful, analytical, and authentically reflect the thinking of {philosopher_name}.'"
    )
    
    system_message_text = "You are a helpful AI assistant highly skilled in creative writing and summarization, specifically for generating engaging introductory paragraphs for roleplaying scenarios based on provided biographical data."
    messages = [
        SystemMessage(content=system_message_text),
        HumanMessage(content=llm_instruction_content)
    ]

    try:
        print(f"\n[PROCESS_INFO_LLM] Calling Groq LLM ({llm_instance.model_name}) for intro: {philosopher_name}...")
        response = await llm_instance.ainvoke(messages) # Use ainvoke for async
        
        if hasattr(response, 'content') and isinstance(response.content, str) and response.content.strip():
            print(f"[PROCESS_INFO_LLM] Successfully received introductory paragraph for {philosopher_name}.")
            return response.content
        else:
            print(f"[PROCESS_INFO_LLM_WARN] LLM returned empty/unexpected response for {philosopher_name}: {response}")
            return (
                f"You are the philosopher named {philosopher_name}. You lived during: {era_context}.\n"
                f"Key Life Events: {life_events}\n"
                f"Academic Environment: {academic_environment}\n\n"
                f"Your objective is to answer questions and engage in discussions as {philosopher_name}, "
                "drawing upon the philosophical aspects, life events, and stylistic traits summarized below. "
                f"Aim to provide responses that are insightful, analytical, and authentically reflect the thinking of {philosopher_name}."
            )

    except Exception as e:
        print(f"[PROCESS_INFO_LLM_ERROR] Error during LLM call for intro ({llm_instance.model_name}): {e}")
        return (
            f"You are the philosopher named {philosopher_name}. You lived during: {era_context}.\n"
            f"Key Life Events: {life_events}\n"
            f"Academic Environment: {academic_environment}\n\n"
            f"Your objective is to answer questions and engage in discussions as {philosopher_name}, "
            "drawing upon the philosophical aspects, life events, and stylistic traits summarized below. "
            f"Aim to provide responses that are insightful, analytical, and authentically reflect the thinking of {philosopher_name}."
        )


async def generate_roleplay_prompt_from_json_string(json_string_data: str, llm_for_intro: ChatGroq = None) -> tuple[str | None, str | None]:
    """
    Xử lý dữ liệu JSON (dưới dạng chuỗi) về một triết gia và tạo ra một prompt chi tiết
    để LLM nhập vai triết gia đó. Sử dụng LLM cho đoạn giới thiệu nếu được cung cấp.
    
    Args:
        json_string_data: Chuỗi JSON chứa hồ sơ triết gia.
        llm_for_intro: Optional - Thể hiện ChatGroq đã được khởi tạo để dùng cho việc tạo giới thiệu.

    Returns:
        Tuple (generated_prompt_string, philosopher_name) hoặc (error_message, None)
    """
    try:
        data = json.loads(json_string_data)
    except json.JSONDecodeError as e:
        return f"Lỗi giải mã JSON: {e}", None

    if "final_synthesized_profile" not in data:
        return "Lỗi: 'final_synthesized_profile' không tìm thấy trong dữ liệu JSON.", None

    profile = data["final_synthesized_profile"]
    philosopher_name = data.get("philosopher_name", "Unknown Philosopher").title()

    prompt_parts = []

    life_events_summary = "Not specified"
    era_context_summary = "an unspecified era"
    academic_env_summary = "not specified in detail"

    if "Biographical_Historical_Context" in profile and isinstance(profile["Biographical_Historical_Context"], dict):
        bio_context_data = profile["Biographical_Historical_Context"]
        life_events_summary = bio_context_data.get("summary_life_events", life_events_summary)
        era_context_summary = bio_context_data.get("summary_era_context", era_context_summary)
        academic_env_summary = bio_context_data.get("summary_academic_environment", academic_env_summary)
    
    introductory_paragraph = await generate_introductory_paragraph_llm(
        philosopher_name,
        life_events_summary,
        era_context_summary,
        academic_env_summary,
        llm_for_intro 
    )
    prompt_parts.append(introductory_paragraph)
    prompt_parts.append("\n") 

    def _add_profile_section(section_title_key: str, display_title: str, section_data: Dict[str, Any]):
        if not section_data or not isinstance(section_data, dict):
            return

        section_content = [f"--- {display_title} ---"]
        has_content = False
        for key, value in section_data.items():
            if not value: 
                continue
            has_content = True
            label = key.replace('_', ' ').capitalize()
            if isinstance(value, list):
                section_content.append(f"{label}:")
                for item in value:
                    if isinstance(item, dict):
                        item_details = []
                        for k_item, v_item in item.items():
                            item_details.append(f"{k_item.replace('_',' ').capitalize()}: {v_item}")
                        section_content.append(f"  * { '; '.join(item_details) }")
                    else:
                        section_content.append(f"  * {item}")
            else:
                section_content.append(f"{label}: {value}")
        
        if has_content:
            prompt_parts.extend(section_content)
            prompt_parts.append("\n")

    category_map = {
        "Major_Works_Core_Content": "MAJOR WORKS & CORE CONTENT",
        "Core_Philosophical_Doctrines_Ideas": "CORE PHILOSOPHICAL DOCTRINES & IDEAS",
        "Views_on_Specific_Philosophical_Topics": "VIEWS ON SPECIFIC PHILOSOPHICAL TOPICS",
        "Philosophical_Relationships_Interactions": "PHILOSOPHICAL RELATIONSHIPS & INTERACTIONS",
        "Critiques_Evaluations_of_Doctrines": "CRITIQUES & EVALUATIONS OF DOCTRINES (for your reference/rebuttal)",
        "Characteristic_Philosophical_Methodology": "CHARACTERISTIC PHILOSOPHICAL METHODOLOGY",
        "Argumentative_Style_Rhetoric": "ARGUMENTATIVE STYLE & RHETORIC",
    }

    for section_key, display_name in category_map.items():
        if section_key in profile:
            _add_profile_section(section_key, display_name, profile[section_key])

    return "\n".join(prompt_parts), philosopher_name


async def main_process_info():
    """
    Main function for standalone execution of processInformation.py.
    Generates prompt.py in the chatAgent directory.
    """
    from dotenv import load_dotenv 
    load_dotenv(os.path.join(PROCESS_WORKSPACE_ROOT, ".env"))

    llm_for_intro = None
    try:
        llm_for_intro = ChatGroq(
            model_name=os.getenv("GROQ_INTRO_MODEL", "mixtral-8x7b-32768"), 
            temperature=0.7,

        )
        print("[PROCESS_INFO_MAIN] LLM for intro generation initialized.")
    except Exception as e:
        print(f"[PROCESS_INFO_MAIN_ERROR] Could not initialize LLM for intro: {e}.")
        print("Ensure GROQ_API_KEY is set in .env. Intro will be template-based.")
    
    json_file_name = "research_karl_marx.json"
    paths_to_check = [
        os.path.join(PROCESS_WORKSPACE_ROOT, json_file_name),
        os.path.join(CWD_PROCESS, json_file_name)
    ]
    actual_json_file_path = None
    for path_check in paths_to_check:
        if os.path.exists(path_check):
            actual_json_file_path = path_check
            break
    
    json_content_to_process = None
    philosopher_name_for_file = "UnknownPhilosopher"

    if actual_json_file_path:
        print(f"[PROCESS_INFO_MAIN] Found research JSON at: {actual_json_file_path}")
        try:
            with open(actual_json_file_path, "r", encoding="utf-8") as f:
                json_content_to_process = f.read()
            try:
                temp_data = json.loads(json_content_to_process)
                philosopher_name_for_file = temp_data.get("philosopher_name", "UnknownPhilosopher").title()
            except json.JSONDecodeError:
                 print("[PROCESS_INFO_MAIN_WARN] Could not parse philosopher_name from JSON, using default.")
        except Exception as e:
            print(f"[PROCESS_INFO_MAIN_ERROR] Error reading {actual_json_file_path}: {e}")
    
    if not json_content_to_process:
        print("[PROCESS_INFO_MAIN_WARN] research_karl_marx.json not found or unreadable. Using sample data for demo.")
        sample_json_data_string = '''
        {
          "philosopher_name": "Demo Philosopher",
          "final_synthesized_profile": {
            "Biographical_Historical_Context": {
              "summary_life_events": "Born in a demo, lived in a simulation.",
              "summary_era_context": "The digital age.",
              "summary_academic_environment": "Educated by algorithms."
            },
            "Major_Works_Core_Content": {"key_works_overview":[{"title":"Sample Work","core_ideas_summary":"About samples."}]}
          }
        }
        '''
        json_content_to_process = sample_json_data_string
        philosopher_name_for_file = "Demo Philosopher"

    print(f"[PROCESS_INFO_MAIN] Generating prompt for: {philosopher_name_for_file}")
    generated_prompt, extracted_philosopher_name = await generate_roleplay_prompt_from_json_string(json_content_to_process, llm_for_intro)
    
    final_philosopher_name = extracted_philosopher_name if extracted_philosopher_name else philosopher_name_for_file

    if generated_prompt and "Lỗi giải mã JSON" not in generated_prompt and "Lỗi: 'final_synthesized_profile'" not in generated_prompt:
        print("\n--- GENERATED ROLEPLAY PROMPT (for file output) ---")

        output_filename = os.path.join(CWD_PROCESS, "prompt.py")
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(f"# -*- coding: utf-8 -*-\n")
                f.write(f"# Auto-generated prompt file for {final_philosopher_name}\n")
                f.write(f"# Generated by chatAgent/processInformation.py\n\n")
                f.write(f"generated_prompt = '''{generated_prompt}'''\n\n")
                f.write("# Example usage:\n")
                f.write("# from prompt import generated_prompt\n")
                f.write("# print(generated_prompt)\n")
            print(f"\n[PROCESS_INFO_MAIN] Successfully wrote generated prompt to {output_filename}")
        except Exception as e:
            print(f"\n[PROCESS_INFO_MAIN_ERROR] Error writing prompt to {output_filename}: {e}")
    else:
        print("\n[PROCESS_INFO_MAIN_ERROR] Could not generate prompt successfully.")
        if generated_prompt: print(f"Details: {generated_prompt}")

if __name__ == '__main__':
    asyncio.run(main_process_info()) 