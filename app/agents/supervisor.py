"""
OMNIA Supervisor Agent — The Brain
Routes user requests to the appropriate specialist agents and orchestrates
multi-step task execution using LLM function calling.

This is the central intelligence of the entire system.
"""
import json
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)


# ── System Prompt (The AI's personality & capabilities) ───────

SYSTEM_PROMPT = """You are OMNIA, an advanced personal AI assistant. You are intelligent, proactive, and efficient.

## Your Capabilities:
1. **Conversation**: Chat naturally, answer questions, provide advice
2. **Web Search**: Search the internet for current information
3. **Location Services**: Find places, businesses, doctors, restaurants using Google Maps
4. **Calendar Management**: View, create, and manage calendar events
5. **Appointment Booking**: Search for providers, check reviews, and help book appointments
6. **File Operations**: Download files, manage documents
7. **Communication**: Send messages via WhatsApp, SMS, or email
8. **System Control**: Execute commands on the user's desktop (with permission)

## Your Personality:
- Professional but friendly
- Proactive: suggest next steps and related actions
- Concise: don't ramble, get to the point
- Safety-conscious: always confirm before taking irreversible actions
- Transparent: explain what you're doing and why

## Rules:
1. ALWAYS ask for confirmation before booking, calling, or spending money
2. When searching for services (doctors, etc.), present at least 3 options with ratings
3. Explain your reasoning when making recommendations
4. If you don't know something, say so — don't make things up
5. When a task has multiple steps, show progress to the user

## Current Date/Time: {current_time}
## User Info: {user_info}
"""


class LLMProvider:
    """
    Abstraction over LLM providers (Gemini / OpenAI).
    Supports streaming responses and function calling.
    """

    def __init__(self):
        self.provider = settings.active_llm_provider
        self._gemini_model = None
        self._openai_client = None
        self._groq_client = None

    async def _get_groq(self):
        """Lazy-load Groq client (OpenAI compatible)."""
        if self._groq_client is None:
            from openai import AsyncOpenAI
            self._groq_client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        return self._groq_client

    async def _get_gemini(self):
        """Lazy-load Gemini client."""
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(
                "gemini-2.0-flash",
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
        return self._gemini_model

    async def _get_openai(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai_client

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Send messages to the LLM and stream the response.
        Yields text chunks as they arrive.
        """
        if self.provider == "groq":
            async for chunk in self._chat_groq(messages, system_prompt, stream):
                yield chunk
        elif self.provider == "gemini":
            async for chunk in self._chat_gemini(messages, system_prompt):
                yield chunk
        elif self.provider == "openai":
            async for chunk in self._chat_openai(messages, system_prompt, stream):
                yield chunk
        else:
            yield "⚠️ No LLM provider configured. Please set GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY in your .env file."

    async def _chat_gemini(
        self, messages: list[dict], system_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Chat with Google Gemini."""
        try:
            model = await self._get_gemini()

            # Convert messages to Gemini format
            gemini_history = []
            for msg in messages[:-1]:  # All except the last
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})

            chat = model.start_chat(history=gemini_history)

            # The last message is the new user input
            last_msg = messages[-1]["content"] if messages else ""
            prompt = f"{system_prompt}\n\nUser: {last_msg}"

            response = await chat.send_message_async(prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            yield f"⚠️ Gemini error: {str(e)}"

    async def _chat_openai(
        self, messages: list[dict], system_prompt: str, stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Chat with OpenAI GPT."""
        try:
            client = await self._get_openai()

            # Build OpenAI messages format
            formatted_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            if stream:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=formatted_messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=2048,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
            else:
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=formatted_messages,
                    temperature=0.7,
                    max_tokens=2048,
                )
                yield response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            yield f"⚠️ OpenAI error: {str(e)}"

    async def _chat_groq(
        self, messages: list[dict], system_prompt: str, stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Chat with Groq API."""
        try:
            client = await self._get_groq()

            formatted_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            if stream:
                response = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=formatted_messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=2048,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
            else:
                response = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=formatted_messages,
                    temperature=0.7,
                    max_tokens=2048,
                )
                yield response.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq error: {e}")
            yield f"⚠️ Groq error: {str(e)}"

    async def chat_complete(
        self, messages: list[dict], system_prompt: str
    ) -> str:
        """Non-streaming version: returns the full response as a single string."""
        full_response = []
        async for chunk in self.chat(messages, system_prompt, stream=False):
            full_response.append(chunk)
        return "".join(full_response)


class SupervisorAgent:
    """
    The main OMNIA brain. Routes user messages through the LLM,
    manages conversation context, and orchestrates tool use.
    """

    def __init__(self):
        self.llm = LLMProvider()

    def _build_system_prompt(self, user_info: Optional[dict] = None) -> str:
        """Build the system prompt with current context."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        info = json.dumps(user_info or {"note": "No user profile loaded"})
        return SYSTEM_PROMPT.format(current_time=now, user_info=info)

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        user_info: Optional[dict] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and stream the AI response.

        Args:
            user_message: The user's text input
            conversation_history: Previous messages in [{"role": "...", "content": "..."}] format
            user_info: User profile data for context
            stream: Whether to stream the response

        Yields:
            Text chunks of the AI response
        """
        system_prompt = self._build_system_prompt(user_info)

        # Add the new user message to history
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        # Stream response from LLM
        async for chunk in self.llm.chat(messages, system_prompt, stream):
            yield chunk


# Singleton instance
supervisor = SupervisorAgent()
