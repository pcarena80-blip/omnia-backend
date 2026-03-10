"""
WebSocket Handler
Real-time bidirectional communication between OMNIA clients and the AI brain.
Supports multi-device sync, voice streaming, and live task updates.
"""
import json
import logging
from typing import Dict, Set
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.agents.supervisor import supervisor

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """
    Manages active WebSocket connections across all devices.
    Supports multi-device for the same user (phone + laptop).
    """

    def __init__(self):
        # user_id -> set of active WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = set()
        self.connections[user_id].add(websocket)
        logger.info(
            f"WebSocket connected: user={user_id}, "
            f"total connections={len(self.connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to ALL devices of a user (multi-device sync)."""
        if user_id in self.connections:
            dead_connections = set()
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_connections.add(ws)
            # Clean up dead connections
            for ws in dead_connections:
                self.connections[user_id].discard(ws)

    async def broadcast_to_user(
        self, user_id: str, message: dict, exclude: WebSocket = None
    ):
        """Broadcast to all user devices except the sender (for sync)."""
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                if ws != exclude:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        pass


# Singleton connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint.
    
    Protocol:
    1. Client connects and sends: {"type": "auth", "token": "jwt_token"}
    2. Server responds: {"type": "connected", "user_id": "..."}
    3. Client sends messages: {"type": "chat", "message": "...", "conversation_id": "..."}
    4. Server streams response: {"type": "chunk", "content": "..."} (multiple)
    5. Server ends response: {"type": "done", "conversation_id": "..."}
    
    Special message types:
    - {"type": "ping"} → {"type": "pong"}
    - {"type": "typing"} → broadcasts to other devices
    - {"type": "task_update", ...} → real-time task progress
    """
    user_id = None

    try:
        # Wait for authentication message
        await websocket.accept()
        auth_data = await websocket.receive_json()

        if auth_data.get("type") != "auth" or "token" not in auth_data:
            await websocket.send_json({
                "type": "error",
                "message": "First message must be authentication: {type: 'auth', token: 'jwt'}"
            })
            await websocket.close()
            return

        # Validate JWT token
        try:
            payload = decode_token(auth_data["token"])
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("No user ID in token")
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Authentication failed: {str(e)}"
            })
            await websocket.close()
            return

        # Register connection
        if user_id not in manager.connections:
            manager.connections[user_id] = set()
        manager.connections[user_id].add(websocket)

        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"WebSocket authenticated: user={user_id}")

        # Message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "chat":
                # Process chat message through the AI
                user_message = data.get("message", "")
                conv_id = data.get("conversation_id", "")
                history = data.get("history", [])

                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue

                # Broadcast to other devices that user is typing
                await manager.broadcast_to_user(
                    user_id,
                    {
                        "type": "user_message",
                        "message": user_message,
                        "conversation_id": conv_id,
                    },
                    exclude=websocket,
                )

                # Stream AI response
                await websocket.send_json({
                    "type": "thinking",
                    "conversation_id": conv_id,
                })

                full_response = []
                async for chunk in supervisor.process_message(
                    user_message, history, stream=True
                ):
                    full_response.append(chunk)
                    # Send chunk to ALL user devices
                    await manager.send_to_user(user_id, {
                        "type": "chunk",
                        "content": chunk,
                        "conversation_id": conv_id,
                    })

                # Notify completion
                await manager.send_to_user(user_id, {
                    "type": "done",
                    "full_content": "".join(full_response),
                    "conversation_id": conv_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == "typing":
                # Broadcast typing indicator to other devices
                await manager.broadcast_to_user(
                    user_id,
                    {"type": "typing", "device": data.get("device", "unknown")},
                    exclude=websocket,
                )

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if user_id:
            manager.disconnect(websocket, user_id)
