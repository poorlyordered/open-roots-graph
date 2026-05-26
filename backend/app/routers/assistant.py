import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.dependencies import get_driver
from app.models.assistant import ChatRequest
from app.services.assistant_service import AssistantService
from app.services.schema_introspector import SchemaIntrospector

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

_service: AssistantService | None = None
_introspector: SchemaIntrospector | None = None


def _get_service() -> AssistantService:
    global _service
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY not configured. Set it in .env",
        )
    if _service is None:
        _service = AssistantService(
            driver=get_driver(),
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
        )
    return _service


def _get_introspector() -> SchemaIntrospector:
    global _introspector
    if _introspector is None:
        _introspector = SchemaIntrospector(get_driver())
    return _introspector


@router.post("/chat")
def chat(request: ChatRequest):
    service = _get_service()

    def event_stream():
        history = [{"role": m.role, "content": m.content} for m in request.history]
        for chunk in service.stream_response(request.message, history, request.mode):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/suggestions")
def suggestions():
    service = _get_service()
    return {"success": True, "data": service.get_suggestions()}


@router.get("/schema")
def schema():
    introspector = _get_introspector()
    return {"success": True, "data": introspector.get_schema_prompt()}
