"""
Tool Services for the Philosopher Research Agent.

This module handles the initialization and configuration of 
external tools, particularly Tavily search functionality.
"""

import os
from langchain_community.tools.tavily_search import TavilySearchResults


def get_tavily_search_tool(max_results: int = 5) -> TavilySearchResults:
    """
    Initialize and return a TavilySearchResults tool instance.
    
    Args:
        max_results: Maximum number of search results to return per query
    
    Returns:
        TavilySearchResults: Configured Tavily search tool
        
    Raises:
        ValueError: If TAVILY_API_KEY is not found in environment
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY not found in environment variables. "
            "Please set this key in your .env file."
        )
    
    return TavilySearchResults(
        max_results=max_results,
        tavily_api_key=api_key,
        include_answer=True,
        search_depth="advanced"
    )


def get_default_search_tool() -> TavilySearchResults:
    """
    Get the default Tavily search tool configuration.
    
    Returns:
        TavilySearchResults: Default configured search tool
    """
    return get_tavily_search_tool(max_results=3) 