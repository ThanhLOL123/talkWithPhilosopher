from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator

class ChatAgentState(TypedDict):
    philosopher_name: str
    roleplay_prompt: str
    chat_history: List[BaseMessage]
    current_user_input: str
    error_message: Annotated[str | None, lambda _old, new: new] 