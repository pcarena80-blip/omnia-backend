"""
Conversation Memory Manager
Maintains sliding window of recent messages + compressed summaries of older ones.
Ensures the AI always has relevant context without exceeding token limits.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation context for the AI.
    
    Strategy:
    - Keep last N messages in full (sliding window)
    - Older messages are summarized using the LLM
    - User facts are stored separately for long-term recall
    """

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self._summaries: dict = {}  # conversation_id -> summary text

    def get_context_messages(
        self,
        messages: List[dict],
        system_summary: Optional[str] = None,
    ) -> List[dict]:
        """
        Build context window from message history.
        Keeps recent messages and prepends a summary of older ones.

        Args:
            messages: Full conversation history [{"role": "...", "content": "..."}]
            system_summary: Optional summary of earlier conversation

        Returns:
            List of messages for the LLM context window
        """
        if len(messages) <= self.window_size:
            return messages

        # Split into old and recent
        old_messages = messages[:-self.window_size]
        recent_messages = messages[-self.window_size:]

        # Create a context with summary
        context = []
        if system_summary:
            context.append({
                "role": "system",
                "content": f"Summary of earlier conversation: {system_summary}",
            })
        elif old_messages:
            # Simple summary: just the first and last old messages
            preview = f"[{len(old_messages)} earlier messages. First: '{old_messages[0]['content'][:100]}...']"
            context.append({
                "role": "system",
                "content": f"Earlier context: {preview}",
            })

        context.extend(recent_messages)
        return context

    async def summarize_conversation(
        self, messages: List[dict], llm_func=None
    ) -> str:
        """
        Generate a summary of a conversation using the LLM.
        Used when conversations get too long.
        """
        if not messages:
            return ""

        # Simple extractive summary for now
        key_points = []
        for msg in messages:
            if msg["role"] == "user" and len(msg["content"]) > 10:
                key_points.append(f"User asked: {msg['content'][:100]}")
            elif msg["role"] == "assistant" and len(msg["content"]) > 10:
                key_points.append(f"Assistant: {msg['content'][:100]}")

        return " | ".join(key_points[:10])


# Singleton
conversation_memory = ConversationMemory()
