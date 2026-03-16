from typing import Literal

from pydantic import BaseModel, Field


class DecisionResult(BaseModel):
    decision: Literal["A", "B", "C"]
    confidence: int = Field(ge=0, le=100)
    reasoning: list[str] = Field(min_length=3, max_length=3)
    risks: list[str] = Field(min_length=2, max_length=2)
    assumptions: list[str] = Field(min_length=2, max_length=2)
