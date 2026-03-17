from typing import List, Literal

from pydantic import BaseModel


class ConsistencyAudit(BaseModel):
    """
    Result of a consistency audit over an agent output.

    - is_consistent: whether the reasoning supports the selected decision
    - severity: how serious the inconsistency is
    - issues: list of detected problems
    - explanation: short human-readable explanation
    """

    is_consistent: bool
    severity: Literal["none", "low", "medium", "high"]
    issues: List[str]
    explanation: str
