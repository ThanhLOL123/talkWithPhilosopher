import json
import re
from typing import Dict, List, Any
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import HumanMessage, SystemMessage

from .state import PhilosopherResearchState, ALL_RESEARCH_CATEGORIES


def load_initial_state_node_logic(
    philosopher_name: str
) -> Dict[str, Any]:
    """
    Initialize the research state for sequential category processing.
    
    Args:
        philosopher_name: Name of the philosopher to research
        
    Returns:
        Dict containing initial state values
    """
    print(f"[NODE] Loading initial state for: {philosopher_name}")
    return {
        "philosopher_name": philosopher_name,
        "all_categories": ALL_RESEARCH_CATEGORIES,
        "current_category_index": 0,
        "current_category_name": None,
        "category_specific_queries": [],
        "category_specific_search_results": [],
        "current_category_extracted_info": [],
        "accumulated_extracted_information": {category: [] for category in ALL_RESEARCH_CATEGORIES},
        "final_synthesized_profile": None,
        "total_generated_queries_count": 0,
        "total_search_results_count": 0,
        "error_messages": [],
        "refinement_iterations": 0
    }


def select_next_category_node_logic(state: PhilosopherResearchState) -> Dict[str, Any]:
    """
    Selects the next category to process or determines if all categories are done.
    Updates current_category_name and resets category-specific temp fields.
    """
    current_index = state["current_category_index"]
    all_categories = state["all_categories"]
    
    if current_index < len(all_categories):
        current_category = all_categories[current_index]
        print(f"[NODE] Selecting category {current_index + 1}/{len(all_categories)}: {current_category}")
        return {
            "current_category_name": current_category,
            "category_specific_queries": [],
            "category_specific_search_results": [],
            "current_category_extracted_info": []
        }
    else:
        print("[NODE] All categories processed. Proceeding to final synthesis.")
        return {
            "current_category_name": None
        }


def generate_queries_for_category_node_logic(
    state: PhilosopherResearchState,
    llm: ChatGroq
) -> Dict[str, Any]:
    """
    Generate search queries for the current category.
    """
    philosopher_name = state["philosopher_name"]
    current_category_name = state["current_category_name"]

    if not current_category_name:
        error_msg = "[ERROR] current_category_name is not set in generate_queries_for_category_node_logic."
        print(error_msg)
        return {"category_specific_queries": [], "error_messages": state.get("error_messages", []) + [error_msg]}

    print(f"[NODE] Generating queries for: {philosopher_name} - Category: {current_category_name}")

    category_descriptions = {
        ALL_RESEARCH_CATEGORIES[0]: "Biographical details, life events, historical and cultural context, academic environment.",
        ALL_RESEARCH_CATEGORIES[1]: "Major written works, their core content, objectives, arguments, and publication context.",
        ALL_RESEARCH_CATEGORIES[2]: "Central philosophical concepts, main arguments/theses, philosophical system, and contributions to specific fields of philosophy.",
        ALL_RESEARCH_CATEGORIES[3]: "Views on specific philosophical topics like reality, God, knowledge, ethics, politics, aesthetics.",
        ALL_RESEARCH_CATEGORIES[4]: "Philosophers who influenced them, thinkers they influenced, and significant dialogues or debates.",
        ALL_RESEARCH_CATEGORIES[5]: "Main criticisms of their doctrines, identified strengths and weaknesses, and any rebuttals.",
        ALL_RESEARCH_CATEGORIES[6]: "Characteristic philosophical methodology, approach to research, or argumentative style.",
        ALL_RESEARCH_CATEGORIES[7]: "Typical presentation style (dialogues, treatises, etc.), rhetorical features, and types of evidence or reasoning used."
    }
    category_focus = category_descriptions.get(current_category_name, "general aspects")

    try:
        system_prompt = f"""You are an expert philosophy researcher. Your task is to generate 2-5 specific and distinct search queries (in English) to gather detailed information about the philosopher: {philosopher_name}.
Focus *only* on the following category: **{current_category_name}**
Description of the category focus: {category_focus}

Ensure queries are targeted and help gather information for this specific category. Queries should be suitable for a web search engine.
Output format: MUST be A JSON array of strings, where each string is a search query.
Example query for Plato, category "{ALL_RESEARCH_CATEGORIES[0]}": "Plato early life education Athens Socratic influence"
Example query for Plato, category "{ALL_RESEARCH_CATEGORIES[2]}": "Plato theory of Forms definition examples criticisms"
"""
        user_prompt = f"Generate search queries for {philosopher_name} regarding {current_category_name}."

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = llm.invoke(messages)
        
        queries_list = []
        raw_content = response.content.strip()
        
        cleaned_content = raw_content
        if cleaned_content.startswith("```json"): 
            cleaned_content = cleaned_content[7:]
        if cleaned_content.endswith("```"): 
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()

        try:
            queries_list = json.loads(cleaned_content)
            if not isinstance(queries_list, list) or not all(isinstance(q, str) for q in queries_list):
                raise ValueError(f"Parsed content is not a list of strings. Parsed: {queries_list}")
            print(f"[NODE] Successfully parsed {len(queries_list)} queries for {current_category_name}. Content used: '{cleaned_content[:100]}...'")
        except (json.JSONDecodeError, ValueError) as parse_error:
            error_msg = f"Error parsing LLM response for query generation ({current_category_name}): {str(parse_error)}. \n  Raw Content from LLM: '{raw_content[:150]}...'"
            print(f"[WARN] {error_msg}")
            current_errors = state.get("error_messages", []) + [error_msg]
            queries_list = [f"{philosopher_name} {current_category_name.replace('_', ' ')} details", f"{philosopher_name} {category_focus[:50]} information"]
            return {"category_specific_queries": queries_list, "error_messages": current_errors}

        return {"category_specific_queries": queries_list}
        
    except Exception as e:
        error_msg = f"Unexpected error in generate_queries_for_category_node_logic ({current_category_name}): {str(e)}"
        print(f"[ERROR] {error_msg}")
        current_errors = state.get("error_messages", []) + [error_msg]
        fallback_queries = [f"{philosopher_name} {current_category_name.replace('_', ' ')} overview"]
        return {"category_specific_queries": fallback_queries, "error_messages": current_errors}


def tavily_search_for_category_node_logic(
    state: PhilosopherResearchState,
    tavily_tool: TavilySearchResults
) -> Dict[str, Any]:
    """
    Perform web searches for the current category's queries.
    """
    queries = state["category_specific_queries"]
    current_category_name = state.get("current_category_name", "Unknown Category")
    philosopher_name = state["philosopher_name"]
    print(f"[NODE] Performing Tavily search for {philosopher_name} - Category: {current_category_name} with {len(queries)} queries.")
    
    if not queries:
        print(f"[WARN] No queries to search for in category: {current_category_name}.")
        return {"category_specific_search_results": []}
    
    all_results = []
    try:
        for query_idx, query in enumerate(queries):
            print(f"  Searching ({query_idx+1}/{len(queries)}): {query}")
            try:
                results = tavily_tool.invoke({"query": query})
                if isinstance(results, list):
                    for result_item in results:
                        if isinstance(result_item, dict):
                            all_results.append({
                                "query": query,
                                "category_searched": current_category_name,
                                "url": result_item.get("url", ""),
                                "title": result_item.get("title", ""),
                                "content": result_item.get("content", ""),
                                "tavily_answer": result_item.get("answer", None),
                                "score": result_item.get("score", 0.0)
                            })
            except Exception as search_error:
                error_msg = f"Search error for query '{query}' (Category: {current_category_name}): {str(search_error)}"
                print(f"[WARN] {error_msg}")
                all_results.append({"query": query, "category_searched": current_category_name, "error": error_msg, "url": "", "title": "", "content": "", "score": 0.0})
        
        print(f"[NODE] Found {len(all_results)} results for category {current_category_name}.")
        return {"category_specific_search_results": all_results}
        
    except Exception as e:
        error_msg = f"Error in Tavily search process for category {current_category_name}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        current_errors = state.get("error_messages", []) + [error_msg]
        return {"category_specific_search_results": [], "error_messages": current_errors}


def extract_information_for_category_node_logic(
    state: PhilosopherResearchState,
    llm: ChatGroq
) -> Dict[str, Any]:
    """
    Extract structured information from search results for the current category.
    """
    search_results = state["category_specific_search_results"]
    philosopher_name = state["philosopher_name"]
    current_category_name = state.get("current_category_name", "Unknown Category")
    print(f"[NODE] Extracting info for {philosopher_name} - Category: {current_category_name} from {len(search_results)} results.")
    
    extracted_for_category = []
    if not search_results:
        print(f"[WARN] No search results to process for extraction in category: {current_category_name}.")
        return {"current_category_extracted_info": []}

    category_structure_prompts = {
        ALL_RESEARCH_CATEGORIES[0]: "Focus on `life_events` (list of strings like birth/death, education, key events), `era_context` (string describing historical/cultural context), and `academic_environment` (list of strings about teachers, peers, school of thought).",
        ALL_RESEARCH_CATEGORIES[1]: "Identify `key_works` (list of dicts: `title`, `summary` of content/arguments) and `publication_info` (list of strings like 'Work Title, c. Year').",
        ALL_RESEARCH_CATEGORIES[2]: "Detail `central_concepts` (list of dicts: `concept_name`, `explanation`), `main_arguments_theses` (list of strings), `philosophical_system_description` (string, if any), and `contributions_to_fields` (list of strings like 'Metaphysics: Contribution').",
        ALL_RESEARCH_CATEGORIES[3]: "Extract `topic_views` (list of dicts: `topic` like 'Nature of Reality', `view_summary` string).",
        ALL_RESEARCH_CATEGORIES[4]: "List `influencers` (strings of names/schools), `influenced_others` (strings of names/schools), and `dialogues_debates` (list of dicts: `interlocutor`, `discussion_summary`).",
        ALL_RESEARCH_CATEGORIES[5]: "Document `main_critiques` (list of strings, with source if possible), `strengths_weaknesses` (list of dicts: `aspect`, `evaluation`), and `rebuttals` (list of strings).",
        ALL_RESEARCH_CATEGORIES[6]: "Describe `methodology_description` (string of their primary method(s)) and provide `method_examples` (list of strings).",
        ALL_RESEARCH_CATEGORIES[7]: "Outline `presentation_style` (string like 'Dialogues'), `rhetorical_features` (list of strings like 'Use of metaphor'), and `evidence_types_used` (list of strings)."
    }
    extraction_focus_prompt = category_structure_prompts.get(current_category_name, "general philosophical information relevant to the category.")

    try:
        for i, result_item in enumerate(search_results):
            if not result_item.get("content") or result_item.get("error"):
                print(f"[INFO] Skipping search result {i+1} for category {current_category_name} due to missing content or error.")
                continue
            print(f"  Extracting from search result {i+1}/{len(search_results)} for {current_category_name}: {result_item.get('title','No Title')[:50]}...")
            try:
                system_prompt = f"""You are a textual analyst specializing in philosophy. Extract information about {philosopher_name} from the provided text, focusing *only* on aspects relevant to the category: **{current_category_name}**.

Specific extraction focus for this category: {extraction_focus_prompt}

Present the extracted information for this category as a JSON object. If specific sub-fields are not found, use empty lists or null. For example, if extracting for "{ALL_RESEARCH_CATEGORIES[0]}", the JSON might look like: 
`{{"life_events\": [\"Born...\", \"Studied...\"], \"era_context\": \"Lived during...\", \"academic_environment\": []}}`

Extract information *only* from the provided text. Do not infer or add external knowledge. Return a single JSON object representing the structured information for *this category only* based on the text.
"""
                user_prompt = f"""Text about {philosopher_name} (Source: {result_item.get('url', 'N/A')}):
{result_item['content'][:3000]}...

Extract information relevant to **{current_category_name}** and structure it as a JSON object based on the focus: {extraction_focus_prompt}."""

                messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                response = llm.invoke(messages)
                
                extracted_item_data = {}
                try:
                    content_str = response.content.strip()
                    if content_str.startswith("```json"): content_str = content_str[7:]
                    if content_str.endswith("```"): content_str = content_str[:-3]
                    content_str = content_str.strip()
                    if not content_str: raise ValueError("LLM returned empty content for category extraction.")
                    extracted_item_data = json.loads(content_str)
                    if not isinstance(extracted_item_data, dict):
                         extracted_item_data = {"error": "LLM did not return a dict for category extraction", "raw_content": content_str}
                except (json.JSONDecodeError, ValueError) as parse_error:
                    error_msg = f"JSON parsing error for category '{current_category_name}' from {result_item.get('url', 'N/A')}: {str(parse_error)}. LLM Raw: {response.content[:100]}..."
                    print(f"[WARN] {error_msg}")
                    extracted_item_data = {"error": error_msg, "text_snippet": result_item['content'][:200] + "..."}

                extracted_item_data["_source_document_metadata"] = {"url": result_item.get("url", ""), "title": result_item.get("title", ""), "query": result_item.get("query", "")}
                extracted_for_category.append(extracted_item_data)
                    
            except Exception as extract_error:
                error_msg = f"Error during specific extraction for category '{current_category_name}' from {result_item.get('url', 'unknown')}: {str(extract_error)}"
                print(f"[ERROR] {error_msg}")
                extracted_for_category.append({"error": error_msg, "_source_document_metadata": {"url": result_item.get("url", ""), "title": result_item.get("title", ""), "query": result_item.get("query", "") }})
        
        return {"current_category_extracted_info": extracted_for_category}
        
    except Exception as e:
        error_msg = f"Unexpected error in extract_information_for_category_node_logic ({current_category_name}): {str(e)}"
        print(f"[ERROR] {error_msg}")
        current_errors = state.get("error_messages", []) + [error_msg]
        return {"current_category_extracted_info": [], "error_messages": current_errors}


def accumulate_and_increment_category_node_logic(state: PhilosopherResearchState) -> Dict[str, Any]:
    """
    Accumulates extracted information for the processed category and increments the category index.
    """
    current_category_name = state["current_category_name"]
    current_category_extracted_info = state["current_category_extracted_info"]
    accumulated_info = state["accumulated_extracted_information"].copy()
    current_index = state["current_category_index"]
    
    # Lấy các bộ đếm hiện tại
    current_total_queries = state.get("total_generated_queries_count", 0)
    current_total_results = state.get("total_search_results_count", 0)

    # Cập nhật bộ đếm
    new_total_queries = current_total_queries + len(state.get("category_specific_queries", []))
    new_total_results = current_total_results + len(state.get("category_specific_search_results", []))

    if not current_category_name:
        error_msg = "[ERROR] current_category_name is not set in accumulate_and_increment_category_node_logic."
        print(error_msg)
        return {"error_messages": state.get("error_messages", []) + [error_msg], "current_category_index": current_index + 1}

    accumulated_info[current_category_name].extend(current_category_extracted_info)

    print(f"[NODE] Accumulated {len(current_category_extracted_info)} new items for category: {current_category_name}.")
    print(f"  Total items for {current_category_name}: {len(accumulated_info.get(current_category_name, []))}")

    next_index = current_index + 1
    return {
        "accumulated_extracted_information": accumulated_info,
        "current_category_index": next_index,
        "total_generated_queries_count": new_total_queries,
        "total_search_results_count": new_total_results
    }


def synthesize_final_profile_node_logic(
    state: PhilosopherResearchState,
    llm: ChatGroq
) -> Dict[str, Any]:
    """
    Synthesize all accumulated category-specific information into a final profile.
    """
    philosopher_name = state["philosopher_name"]
    accumulated_information = state["accumulated_extracted_information"]
    all_categories_list = state["all_categories"]
    print(f"[NODE] Synthesizing final profile for {philosopher_name} from accumulated information across {len(all_categories_list)} categories.")

    if not accumulated_information or all(not data for data in accumulated_information.values()):
        print("[WARN] No accumulated information to synthesize for final profile.")
        return {"final_synthesized_profile": {"error": "No accumulated information available for synthesis."}}

    try:
        synthesis_input_text = f"Comprehensive Extracted Data for {philosopher_name}:\n\n"
        for category_name in all_categories_list:
            category_data = accumulated_information.get(category_name, [])
            synthesis_input_text += f"--- Category: {category_name.replace('_',' ')} ---\n"
            if category_data:
                for item_idx, item_info in enumerate(category_data[:3]):
                    line_url_part = f"  Source {item_idx+1} (URL: {item_info.get('_source_document_metadata',{}).get('url','N/A')}):"
                    synthesis_input_text += line_url_part + "\n"
                    
                    item_content_for_prompt = {k: v for k, v in item_info.items() if k != "_source_document_metadata"}
                    json_dump_str = json.dumps(item_content_for_prompt, ensure_ascii=False, indent=4)
                    synthesis_input_text += f"    {json_dump_str}\n"
                if len(category_data) > 3:
                    synthesis_input_text += f"    (...and {len(category_data) - 3} more sources for this category...)\n"
                synthesis_input_text += "\n"
            else:
                synthesis_input_text += "  (No specific information extracted for this category)\n\n"

        if len(synthesis_input_text) > 30000:
            print(f"[WARN] Final synthesis input text is very long ({len(synthesis_input_text)} chars), truncating.")
            synthesis_input_text = synthesis_input_text[:30000] + "\n...[FINAL SYNTHESIS INPUT TRUNCATED]..."

        cat_bio = all_categories_list[0]
        cat_works = all_categories_list[1]
        cat_doctrines = all_categories_list[2]
        cat_topics = all_categories_list[3]
        cat_relations = all_categories_list[4]
        cat_critiques = all_categories_list[5]
        cat_methodology = all_categories_list[6]
        cat_style = all_categories_list[7]

        system_prompt = f"""You are a distinguished philosopher and historian of philosophy. Your task is to synthesize the provided comprehensive extracted information about {philosopher_name} into a final, coherent, and well-structured profile. The information has been pre-categorized.

The final profile must follow these 8 categories strictly. For each category, synthesize ALL relevant information from the provided data snippets for that category, remove redundancy, ensure coherence, and present a clear, encyclopedic overview. If no significant information was found for a category or sub-topic after reviewing all snippets, indicate that explicitly (e.g., "No specific details found regarding their early education.").

Final Output Structure (JSON Object with 8 top-level keys matching the category names):

1.  `{cat_bio}`:
    *   `summary_life_events`: (String) Coherent narrative of key life events and education.
    *   `summary_era_context`: (String) Synthesized description of the historical, cultural, and philosophical era.
    *   `summary_academic_environment`: (String) Overview of influential teachers, peers, and schools of thought.

2.  `{cat_works}`:
    *   `key_works_overview`: (List of Dictionaries) Each dict: `{{\"title\": \"Work Title\", \"core_ideas_summary\": \"Synthesized summary of its main themes, arguments, and objectives.\"}}`.
    *   `context_of_works`: (String) General context or evolution of their writings.

3.  `{cat_doctrines}`:
    *   `central_concepts_explained`: (List of Dictionaries) Each dict: `{{\"concept_name\": \"Concept\", \"detailed_explanation\": \"Comprehensive synthesized explanation of the concept.\"}}`.
    *   `key_arguments_theses_summary`: (String) Narrative summarizing their most important philosophical claims and how they are argued.
    *   `philosophical_system_overview`: (String) Description of how their ideas form a coherent system (if applicable).
    *   `main_contributions_by_field`: (List of Dictionaries) Each dict: `{{\"field\": \"e.g., Metaphysics\", \"contribution_summary\": \"Synthesized summary of their contribution to this field.\"}}`.

4.  `{cat_topics}`:
    *   `topic_stances`: (List of Dictionaries) Each dict: `{{\"topic\": \"e.g., Nature of Reality\", \"synthesized_stance\": \"Detailed, synthesized view on the topic.\"}}`.

5.  `{cat_relations}`:
    *   `key_influencers_on_philosopher`: (String) Narrative on who influenced them and how.
    *   `impact_on_later_philosophy`: (String) Narrative on their influence on subsequent thinkers/movements.
    *   `significant_dialogues_debates`: (String) Summary of important debates or dialogues they engaged in.

6.  `{cat_critiques}`:
    *   `summary_of_main_critiques`: (String) Overview of major criticisms against their work.
    *   `overall_strengths_weaknesses`: (String) Synthesized evaluation of their philosophy's strong and weak points.
    *   `summary_of_rebuttals`: (String) How they (or followers) responded to key criticisms, if known.

7.  `{cat_methodology}`:
    *   `methodology_explained`: (String) Detailed explanation of their primary philosophical method(s) with examples.

8.  `{cat_style}`:
    *   `writing_style_summary`: (String) Description of their typical presentation style and rhetorical features.
    *   `reasoning_and_evidence_patterns`: (String) How they typically construct arguments and what evidence they use.

Ensure the output is a single, valid JSON object where keys are the category names like "{cat_bio}", etc.
"""

        user_prompt = f"""Synthesize the accumulated extracted information about {philosopher_name} into a comprehensive 8-category profile.

Accumulated Extracted Data (organized by category from multiple sources):
{synthesis_input_text}

Produce the final JSON profile with the 8 specified top-level keys corresponding to the category names provided in the system message: {cat_bio}, {cat_works}, {cat_doctrines}, {cat_topics}, {cat_relations}, {cat_critiques}, {cat_methodology}, {cat_style}.
"""
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = llm.invoke(messages)
        
        profile = {}
        try:
            content_str = response.content.strip()
            if content_str.startswith("```json"): content_str = content_str[7:]
            if content_str.endswith("```"): content_str = content_str[:-3]
            content_str = content_str.strip()
            if not content_str: raise ValueError("LLM returned empty content for final synthesis.")
            profile = json.loads(content_str)
            
            if not isinstance(profile, dict) or not all(cat_name in profile for cat_name in all_categories_list):
                print(f"[WARN] Final synthesized profile for {philosopher_name} might not have all 8 category keys as per 'all_categories_list'. Found: {list(profile.keys())}")

            profile["_final_synthesis_metadata"] = {
                "philosopher_name": philosopher_name,
                "processed_categories_count": len(all_categories_list),
                "synthesis_llm_model": llm.model_name if hasattr(llm, 'model_name') else 'unknown'
            }
            print(f"[NODE] Successfully synthesized final profile for {philosopher_name}.")
        except (json.JSONDecodeError, ValueError) as parse_error:
            error_msg = f"JSON parsing/validation error during final synthesis: {str(parse_error)}. LLM Raw: {response.content[:200]}..."
            print(f"[WARN] {error_msg}")
            profile = {"error": "Unable to properly synthesize the final 8-category JSON profile.", "details": error_msg, "raw_synthesis_attempt": response.content}
            profile["_final_synthesis_metadata"] = {"philosopher_name": philosopher_name, "synthesis_error": True}
        
        return {"final_synthesized_profile": profile}
        
    except Exception as e:
        error_msg = f"Unexpected error in synthesize_final_profile_node_logic: {str(e)}"
        print(f"[ERROR] {error_msg}")
        current_errors = state.get("error_messages", []) + [error_msg]
        return {"final_synthesized_profile": {"error": error_msg}, "error_messages": current_errors}