import json

from magi.llm_client import LLMClient
from magi.models.decision_result import DecisionResult

BASELINE_SYSTEM_PROMPT = """
You are a decision-support model.

Evaluate the scenario and choose exactly one option from the options provided.
Use only the information in the scenario.

Do not invent new options.
Do not add extra commentary.
Do not use markdown.
Return strictly valid JSON only.

Use exactly this schema:
{
  "decision": "A or B or C",
  "confidence": 0,
  "reasoning": [
    "short point 1",
    "short point 2",
    "short point 3"
  ],
  "risks": [
    "short point 1",
    "short point 2"
  ],
  "assumptions": [
    "short point 1",
    "short point 2"
  ]
}

Constraints:
- reasoning must contain exactly 3 items
- risks must contain exactly 2 items
- assumptions must contain exactly 2 items
- confidence must be an integer from 0 to 100
- each item must be a single short sentence
- be concise, specific, and structured
""".strip()


class SingleLLMBaseline:
    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model
        self.client = LLMClient(model=model)

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if not text:
            raise ValueError("Baseline model returned an empty response.")

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError(
                f"Baseline model returned no valid JSON object.\nRaw response:\n{text}"
            )

        return text[start : end + 1]

    def _normalize_data(self, data: dict) -> dict:
        decision = str(data.get("decision", "B")).strip().upper()
        if decision not in {"A", "B", "C"}:
            decision = "B"

        confidence = data.get("confidence", 50)
        try:
            confidence = int(confidence)
        except Exception:
            confidence = 50
        confidence = max(0, min(100, confidence))

        def normalize_list(value, fallback_item: str, max_items: int) -> list[str]:
            if not isinstance(value, list):
                value = []

            cleaned = []
            for item in value:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        cleaned.append(text)
                elif isinstance(item, dict):
                    flattened = " ".join(
                        str(v).strip() for v in item.values() if str(v).strip()
                    ).strip()
                    if flattened:
                        cleaned.append(flattened)

            if not cleaned:
                cleaned = [fallback_item]

            return cleaned[:max_items]

        reasoning = normalize_list(
            data.get("reasoning"),
            fallback_item="No reasoning provided.",
            max_items=3,
        )
        risks = normalize_list(
            data.get("risks"),
            fallback_item="No major risks identified.",
            max_items=2,
        )
        assumptions = normalize_list(
            data.get("assumptions"),
            fallback_item="No explicit assumptions stated.",
            max_items=2,
        )

        while len(reasoning) < 3:
            reasoning.append("Additional reasoning not provided.")
        while len(risks) < 2:
            risks.append("Additional risk not provided.")
        while len(assumptions) < 2:
            assumptions.append("Additional assumption not provided.")

        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "risks": risks,
            "assumptions": assumptions,
        }

    def evaluate(self, scenario: str, retries: int = 3) -> DecisionResult:
        last_error = None

        for _ in range(retries):
            try:
                raw = self.client.ask(
                    system_prompt=BASELINE_SYSTEM_PROMPT,
                    user_prompt=scenario,
                )

                if not raw or not raw.strip():
                    raise ValueError("Baseline model returned no content.")

                json_text = self._extract_json(raw)
                data = json.loads(json_text)
                normalized = self._normalize_data(data)

                return DecisionResult.model_validate(normalized)

            except Exception as e:
                last_error = e

        raise ValueError(
            f"SingleLLMBaseline failed after {retries} attempts: {last_error}"
        )
