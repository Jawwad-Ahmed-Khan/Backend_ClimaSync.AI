"""Centralized core logic to enforce limits over potentially infinite datastreams."""

from typing import TypeVar, Sequence
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel):
    """Standardized shell structure defining offset and absolute array dimensions."""
    data: Sequence[T]
    total: int
    limit: int
    offset: int
    has_more: bool

class PaginationService:
    """Core domain math decoupling route endpoints from SQL limit algorithms."""

    @staticmethod
    def calculate_bounds(limit: int = 100, offset: int = 0, ceiling: int = 500) -> tuple[int, int]:
        """Safeguards server memory by clamping request limits before database touches."""
        sanitized_limit = max(1, min(limit, ceiling))
        sanitized_offset = max(0, offset)
        return sanitized_limit, sanitized_offset

    @classmethod
    def wrap_payload(cls, data: Sequence[T], total: int, limit: int, offset: int) -> PaginatedResponse:
        """Constructs a deterministic dictionary interface so the frontend understands page tracking natively."""
        has_more = (offset + len(data)) < total
        return PaginatedResponse(
            data=data,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
