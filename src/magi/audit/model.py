from typing import List, Literal

from pydantic import BaseModel


class ConsistencyAudit(BaseModel):
    supports_selected_option: bool
    acknowledges_tradeoffs: bool
    implicitly_supports_alternative: bool
    reasoning_is_generic: bool
    direct_contradiction_present: bool

    is_consistent: bool
    severity: Literal["none", "low", "medium", "high"]
    issues: list[str]
    explanation: str
