import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.config import settings
from app.schemas import (
    HealthResponse,
    ChatRequest,
    ChatResponse,
    SessionMessagesResponse,
    MessageHistoryItem
)
from app.models import Message
from app.services.llm_service import llm_service
from app.services.cache_service import cache_service

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """
    Returns 200 once app is running, database is reachable, and key pool is loaded.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database unreachable: {str(e)}"
        )
    
    keys_count = len(settings.key_pool)
    return HealthResponse(
        status="ok",
        keys_configured=keys_count,
        cache_enabled=cache_service.is_enabled
    )

@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    payload: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure"),
    db: Session = Depends(get_db)
):
    """
    Processes chat requests with multi-turn history, key failover, and caching.
    Persists user message and assistant reply to SQLite on success.
    Does NOT persist failed requests.
    """
    # 1. Retrieve conversation history for session_id (oldest first)
    stored_messages = (
        db.query(Message)
        .filter(Message.session_id == payload.session_id)
        .order_by(Message.id.asc())
        .all()
    )

    # 2. Build full message list for LLM
    llm_messages = []
    if payload.system_prompt:
        llm_messages.append({"role": "system", "content": payload.system_prompt})

    for m in stored_messages:
        llm_messages.append({"role": m.role, "content": m.content})

    llm_messages.append({"role": "user", "content": payload.message})

    # 3. Call LLM Service
    try:
        reply_text, metadata = await llm_service.generate_response(
            messages=llm_messages,
            simulate_failure_header=x_simulate_failure
        )
    except HTTPException:
        # Re-raise HTTPExceptions (e.g. 503) without saving to DB
        raise
    except Exception as e:
        # Do not expose internal stack traces
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="all providers unavailable"
        )

    # 4. On successful LLM response, persist to SQLite
    now_iso = datetime.now(timezone.utc).isoformat()
    user_record = Message(
        session_id=payload.session_id,
        role="user",
        content=payload.message,
        created_at=now_iso
    )
    
    assistant_meta_dict = {
        "resolution_source": metadata.resolution_source,
        "input_tokens": metadata.input_tokens,
        "output_tokens": metadata.output_tokens
    }
    assistant_record = Message(
        session_id=payload.session_id,
        role="assistant",
        content=reply_text,
        metadata_=json.dumps(assistant_meta_dict),
        created_at=now_iso
    )

    try:
        db.add(user_record)
        db.add(assistant_record)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist message history: {str(e)}"
        )

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply_text,
        metadata=metadata
    )

@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
    response_model_exclude_none=True
)
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """
    Returns the stored history of one session from SQLite, oldest first,
    without the system prompt. Unknown session returns HTTP 404.
    """
    trimmed_id = session_id.strip()
    messages = (
        db.query(Message)
        .filter(Message.session_id == trimmed_id)
        .order_by(Message.id.asc())
        .all()
    )

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="session not found"
        )

    history_items = []
    for m in messages:
        item = MessageHistoryItem(
            role=m.role,
            content=m.content,
            metadata=m.parsed_metadata if m.role == "assistant" else None
        )
        history_items.append(item)

    return SessionMessagesResponse(
        session_id=trimmed_id,
        messages=history_items
    )
