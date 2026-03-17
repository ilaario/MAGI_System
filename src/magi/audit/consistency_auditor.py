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
You are a strict consistency auditor in a multi-agent decision system.

Your role is NOT to evaluate which option is best.
Your role is NOT to propose an alternative decision.

Your ONLY task is to evaluate whether the agent's selected decision is
internally consistent with its own output.

You must check alignment between:
- the selected decision
- the reasoning
- the listed risks
- the assumptions
- the scenario context

--------------------------------
EVALUATION CRITERIA
--------------------------------

1. DECISION SUPPORT
Does the reasoning clearly justify the selected option?
Or is it generic, weak, or not specific to the chosen option?

2. CONTRADICTIONS
Does the agent describe the chosen option as harmful, risky, or undesirable
without properly justifying why it is still selected?

3. ALTERNATIVE SUPPORT
Does the reasoning implicitly support another option more strongly than the chosen one?

4. RISK CONSISTENCY
Do the listed risks significantly undermine the decision?
Are risks acknowledged but still logically compatible with the choice?

5. SPECIFICITY
Is the reasoning concrete and grounded in the scenario,
or vague and interchangeable with any option?

--------------------------------
SEVERITY GUIDELINES
--------------------------------

- "none": Fully consistent. Reasoning clearly supports the decision.
- "low": Minor issues (slightly generic reasoning, but still aligned).
- "medium": Noticeable weaknesses or partial inconsistencies.
- "high": Clear contradiction or reasoning supports another option.

--------------------------------
IMPORTANT RULES
--------------------------------

- Do NOT say which option is better.
- Do NOT re-evaluate the scenario from scratch.
- Judge ONLY internal consistency of the given output.
- Be strict: weak or generic reasoning should NOT be considered fully consistent.
- Prefer flagging issues over being overly lenient.

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------

Return ONLY valid JSON. No extra text.

{
  "is_consistent": true,
  "severity": "none",
  "issues": [],
  "explanation": "Clear, concise explanation of your judgment."
}
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

        return self._parse_response(response)

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
        try:
            response = response.strip()
            response = response[response.find("{") : response.rfind("}") + 1]
            data = json.loads(response)
            return ConsistencyAudit(**data)
        except Exception as e:
            raise ValueError(
                f"Failed to parse auditor response: {e}\nResponse: {response}"
            )
