import os
from typing import Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def get_llm(
    model_name: str = os.getenv("GROQ_MODEL_NAME"),
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    reasoning_format: Optional[str] = "hidden"
) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment variables. "
            "Please set this key in your .env file."
        )
    
    effective_model_name = model_name
    if not effective_model_name:
        effective_model_name = "mixtral-8x7b-32768"

    llm_kwargs = {
        "model_name": effective_model_name,
        "groq_api_key": api_key,
        "temperature": temperature,
        "model_kwargs": {}
    }
    
    if max_tokens is not None:
        llm_kwargs["max_tokens"] = max_tokens
    
    if reasoning_format:
        llm_kwargs["model_kwargs"]["reasoning_format"] = reasoning_format

    if not llm_kwargs["model_kwargs"]:
        del llm_kwargs["model_kwargs"]

    return ChatGroq(**llm_kwargs)


def get_default_llm() -> ChatGroq:
    default_model = os.getenv("GROQ_MODEL_NAME")
    if not default_model:
        default_model = "mixtral-8x7b-32768"

    return get_llm(
        model_name=default_model,
        temperature=0.2,
        max_tokens=4000,
        reasoning_format="hidden"
    ) 