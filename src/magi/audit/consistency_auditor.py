"""
ConsistencyAuditor — Meta-Evaluation Unit

This component acts as a secondary validation layer for agent outputs in the
MAGI system.

It does NOT evaluate which option is best.

Instead, it verifies whether an agent's selected decision is internally
consistent with:
- its reasoning
- its listed risks
- its assumptions
- the provided scenario

The goal is to detect subtle inconsistencies such as:
- reasoning that contradicts the chosen decision
- risks that undermine the selected option
- arguments that implicitly support a different option

The auditor returns a structured ConsistencyAudit object, which can be used
to enrich reports or trigger warnings in the decision pipeline.

This component is designed to complement heuristic checks, not replace them.
"""

import json
from typing import Any

from magi.audit.model import ConsistencyAudit
from magi.llm_client import LLMClient
from magi.models.decision_result import DecisionResult

AUDITOR_SYSTEM_PROMPT = """
You are a strict but fair consistency auditor in a multi-agent decision system.

Your job is NOT to decide which option is best.
Your job is NOT to judge whether the chosen decision is optimal.

Your ONLY task is to evaluate whether the selected decision is internally
supported by the agent's own reasoning, risks, assumptions, and scenario context.

Important:
A decision can still be internally consistent even if it has serious risks.
Acknowledging risks or trade-offs does NOT make a decision inconsistent.

A decision should be marked inconsistent only if:
- the reasoning does not actually support the selected option
- the reasoning more strongly supports another option
- the selected option is described as undesirable without justification
- there is a direct contradiction between the chosen option and the agent's explanation

Do NOT treat normal trade-offs as contradictions.
Do NOT penalize moderate or compromise options just because they have downsides.
Do NOT assume that mentioning risks undermines the choice.

Evaluate the following dimensions:

1. supports_selected_option
Does the reasoning clearly support the selected option?

2. acknowledges_tradeoffs
Are the listed risks and downsides presented as accepted trade-offs rather than contradictions?

3. implicitly_supports_alternative
Does the reasoning appear to favor another option more strongly than the chosen one?

4. reasoning_is_generic
Is the reasoning too generic or weakly grounded in the scenario?

5. direct_contradiction_present
Is there a direct contradiction between the decision and the explanation?

Severity guidance:
- none: clearly consistent
- low: mostly consistent, minor weakness or generic phrasing
- medium: noticeable weakness or ambiguity
- high: clear contradiction or stronger support for another option

Return ONLY valid JSON in this format:

{
  "supports_selected_option": true,
  "acknowledges_tradeoffs": true,
  "implicitly_supports_alternative": false,
  "reasoning_is_generic": false,
  "direct_contradiction_present": false,
  "is_consistent": true,
  "severity": "none",
  "issues": [],
  "explanation": "..."
}

Rules:
- "issues" must be a list of short strings only
- do not return objects inside "issues"
- be strict, but do not confuse trade-offs with contradictions
"""


class ConsistencyAuditor:
    def __init__(self, model: str = "openrouter/free"):
        self.client = LLMClient(model=model)

    def audit(self, scenario: str, result: DecisionResult) -> ConsistencyAudit:
        prompt = self._build_prompt(scenario, result)

        response = self.client.ask(
            system_prompt=AUDITOR_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        parsed = self._parse_response(response)
        return self._normalize_audit(parsed)

    def _build_prompt(self, scenario: str, result: DecisionResult) -> str:
        return f"""
You are a consistency auditor in a multi-agent decision system.

Your task is NOT to choose the best option.

Your task is to evaluate whether the selected decision is internally consistent
with the reasoning, risks, assumptions, and the scenario.

Focus on:
- Does the reasoning actually support the chosen option?
- Do the risks contradict the decision?
- Do the arguments implicitly support another option?
- Is the reasoning specific and grounded, or generic and weak?

Be strict but fair.

Return ONLY valid JSON in this format:
{{
  "is_consistent": true,
  "severity": "none",
  "issues": [],
  "explanation": "..."
}}

SCENARIO:
{scenario}

AGENT OUTPUT:
Decision: {result.decision}
Confidence: {result.confidence}

Reasoning:
{self._format_list(result.reasoning)}

Risks:
{self._format_list(result.risks)}

Assumptions:
{self._format_list(result.assumptions)}
"""

    def _format_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def _parse_response(self, response: str) -> ConsistencyAudit:
        response = response.strip()
        start = response.find("{")
        end = response.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError(
                f"Failed to parse auditor response: no JSON found\nResponse: {response}"
            )

        json_text = response[start : end + 1]
        data = json.loads(json_text)

        issues = data.get("issues", [])
        normalized_issues = []

        for item in issues:
            if isinstance(item, str):
                normalized_issues.append(item)
            elif isinstance(item, dict):
                issue = item.get("issue", "").strip()
                description = item.get("description", "").strip()
                if issue and description:
                    normalized_issues.append(f"{issue}: {description}")
                elif issue:
                    normalized_issues.append(issue)
                elif description:
                    normalized_issues.append(description)

        data["issues"] = normalized_issues

        return ConsistencyAudit.model_validate(data)

    def _normalize_audit(self, audit: ConsistencyAudit) -> ConsistencyAudit:
        # If reasoning supports the choice and there is no direct contradiction,
        # do not allow "high" severity unless it explicitly supports another option.
        if (
            audit.supports_selected_option
            and not audit.direct_contradiction_present
            and not audit.implicitly_supports_alternative
            and audit.severity == "high"
        ):
            audit.severity = "low" if audit.reasoning_is_generic else "none"
            audit.is_consistent = not audit.reasoning_is_generic

        return audit
