from pydantic import BaseModel
from typing import Literal


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    mode: Literal["query", "hypothesis", "research"] = "query"


class StreamChunk(BaseModel):
    type: Literal["text", "cypher", "data", "error", "done"]
    content: str
