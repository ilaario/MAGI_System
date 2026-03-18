from typing import Literal

from pydantic import BaseModel

from ..audit.model import ConsistencyAudit
from .decision_result import DecisionResult


class FinalDecision(BaseModel):
    final_decision: str
    vote_type: Literal["unanimous", "majority", "split"]
    winning_agents: list[str]
    dissenting_agents: list[str]
    results: dict[str, DecisionResult]

    weighted_scores: dict[str, int]
    weighted_winner: str
    agreement_score: float

    consistency_warnings: dict[str, str]
    consistency_notes: dict[str, list[str]]
    audits: dict[str, ConsistencyAudit]
    is_partial: bool
    missing_agents: list[str]

    needs_recovery_round: bool
    recovery_reason: str | None

    summary: str
