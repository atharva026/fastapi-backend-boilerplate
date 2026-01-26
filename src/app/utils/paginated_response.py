from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]

    total: int
    limit: int
    current_page: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int]
    previous_page: Optional[int]