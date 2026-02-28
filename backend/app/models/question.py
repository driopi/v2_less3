from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(description="Question unique id")
    text: str = Field(description="Question text")
