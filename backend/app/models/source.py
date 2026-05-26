from pydantic import BaseModel


class Source(BaseModel):
    id: str
    title: str
    author: str | None = None
    publisher: str | None = None


class SourceListResponse(BaseModel):
    success: bool = True
    data: list[Source] = []
