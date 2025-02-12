from pydantic import BaseModel
from ..models.chat_users import ChatUserRole

class ChatUserUpdate(BaseModel):
    """Schema for updating a chat user."""
    role: ChatUserRole
