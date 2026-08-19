"""Base Pydantic schemas shared across all modules.

All request/response schemas inherit from BaseSchema which sets
from_attributes=True for ORM integration.
"""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with ORM mode enabled."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseSchema):
    """Generic response containing a single message string."""

    message: str
