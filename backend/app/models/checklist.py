from typing import Optional
from typing import Literal

from pydantic import BaseModel


class ChecklistItem(BaseModel):
    category: str
    item: str
    status: Literal["confirmed", "needs_clarification", "not_discussed"]
    notes: Optional[str] = None
