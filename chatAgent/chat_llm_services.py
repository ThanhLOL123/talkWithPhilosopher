from langchain_groq import ChatGroq
import os

def get_chat_llm(model_name: str = None, temperature: float = 0.7):
    try:
        
        effective_model_name = model_name or os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
        
        llm_params = {
            "model_name": effective_model_name,
            "temperature": temperature,
        }

        if "mixtral" in effective_model_name.lower():
            llm_params["model_kwargs"] = {"reasoning_format": "hidden"}
        
        llm = ChatGroq(**llm_params)
        print(f"[LLM SERVICE - CHAT] ChatGroq LLM initialized with model: {llm.model_name}, temp: {temperature}")
        return llm
    except Exception as e:
        print(f"[LLM SERVICE ERROR - CHAT] Failed to initialize ChatGroq: {e}")
        print("Please ensure GROQ_API_KEY is set in your .env file and is valid.")
        print("You can also set GROQ_CHAT_MODEL in your .env to specify a different chat model.")
        return None 