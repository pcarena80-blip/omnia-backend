"""
Chat API Routes
Handles text conversations with the AI assistant.
Supports both REST (request/response) and streaming (SSE) modes.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.agents.supervisor import supervisor


router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ── Request/Response Schemas ──────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # None = new conversation
    stream: bool = True


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    model_used: str


class ConversationItem(BaseModel):
    id: str
    title: str
    updated_at: datetime
    message_count: int


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


# ── Helper Functions ──────────────────────────────────────────


async def _get_or_create_conversation(
    db: AsyncSession, user_id: str, conversation_id: Optional[str]
) -> Conversation:
    """Get existing conversation or create a new one."""
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    # Create new conversation
    conv = Conversation(user_id=user_id)
    db.add(conv)
    await db.flush()
    return conv


async def _get_conversation_history(
    db: AsyncSession, conversation_id: str, limit: int = 20
) -> list[dict]:
    """Get recent messages for context window."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()  # Chronological order

    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]


async def _get_user_info(db: AsyncSession, user_id: str) -> dict:
    """Get user profile info for AI context."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {}
    return {
        "name": user.full_name or user.username,
        "location": user.location,
        "timezone": user.timezone,
        "preferences": user.preferences or {},
    }


# ── Routes ────────────────────────────────────────────────────


@router.post("/send")
async def send_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to OMNIA and get a response.
    Supports streaming (SSE) and non-streaming modes.
    """
    # Get or create conversation
    conversation = await _get_or_create_conversation(
        db, user_id, request.conversation_id
    )

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.flush()

    # Get conversation history for context
    history = await _get_conversation_history(db, conversation.id)
    user_info = await _get_user_info(db, user_id)

    if request.stream:
        # Streaming response (Server-Sent Events)
        async def generate():
            full_response = []
            async for chunk in supervisor.process_message(
                request.message, history[:-1], user_info, stream=True
            ):
                full_response.append(chunk)
                yield f"data: {chunk}\n\n"

            # Save assistant response after streaming completes
            assistant_content = "".join(full_response)
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                model_used=supervisor.llm.provider,
            )
            db.add(assistant_msg)

            # Update conversation title from first message
            if len(history) <= 1:
                conversation.title = request.message[:80]

            await db.commit()

            yield f"data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-Id": conversation.id,
            },
        )
    else:
        # Non-streaming response
        response_text = await supervisor.llm.chat_complete(
            history, supervisor._build_system_prompt(user_info)
        )

        # Save assistant response
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            model_used=supervisor.llm.provider,
        )
        db.add(assistant_msg)

        # Update conversation title from first message
        if len(history) <= 1:
            conversation.title = request.message[:80]

        await db.commit()

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            content=response_text,
            model_used=supervisor.llm.provider,
        )


@router.get("/conversations", response_model=list[ConversationItem])
async def list_conversations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(50)
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Get message count
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        msg_count = len(msg_result.scalars().all())

        items.append(ConversationItem(
            id=conv.id,
            title=conv.title,
            updated_at=conv.updated_at,
            message_count=msg_count,
        ))

    return items


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageItem])
async def get_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return [
        MessageItem(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
