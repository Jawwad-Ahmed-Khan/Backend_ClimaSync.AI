"""Admin messaging service — business logic for chat functionality."""

import uuid
from fastapi import HTTPException

from app.modules.admin.repository import MessageRepository


class AdminMessageService:
    def __init__(self, message_repo: MessageRepository) -> None:
        self.message_repo = message_repo

    async def get_conversations(self, user_id: uuid.UUID) -> list[dict]:
        """List all conversations for a user."""
        return await self.message_repo.get_conversations_for_user(user_id)

    async def get_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get messages for a specific conversation and mark them as read."""
        messages = await self.message_repo.get_messages(conversation_id, limit=limit, offset=offset)
        # Mark as read
        await self.message_repo.mark_messages_read(conversation_id, user_id)
        return messages

    async def send_message(self, sender_id: uuid.UUID, receiver_id: uuid.UUID, content: str) -> dict:
        """Send a message to another user, creating conversation if needed."""
        if sender_id == receiver_id:
            raise HTTPException(status_code=400, detail="Cannot message yourself")

        conv = await self.message_repo.get_or_create_conversation(sender_id, receiver_id)

        msg = await self.message_repo.create_message({
            "conversation_id": conv.conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
        })
        return msg

    async def mark_read(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Mark all messages in a conversation as read."""
        return await self.message_repo.mark_messages_read(conversation_id, user_id)
