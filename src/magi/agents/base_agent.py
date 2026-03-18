import json

from ..llm_client import LLMClient
from ..models.decision_result import DecisionResult


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = LLMClient(model=model)

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if not text:
            raise ValueError(f"{self.name} returned an empty response.")

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end < start:
            raise ValueError(
                f"{self.name} returned no valid JSON object.\nRaw response:\n{text}"
            )

        return text[start : end + 1]

    def _normalize_data(self, data: dict) -> dict:
        # decision fallback
        decision = str(data.get("decision", "B")).strip().upper()
        if decision not in {"A", "B", "C"}:
            decision = "B"

        # confidence fallback + clamp
        confidence = data.get("confidence", 50)
        try:
            confidence = int(confidence)
        except Exception:
            confidence = 50
        confidence = max(0, min(100, confidence))

        # list normalization helper
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
                    # best-effort flattening for weird model outputs
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

        # pad lists if too short
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
                    system_prompt=self.system_prompt,
                    user_prompt=scenario,
                )

                if not raw or not raw.strip():
                    raise ValueError(f"{self.name} returned an empty response.")

                json_text = self._extract_json(raw)
                data = json.loads(json_text)
                normalized = self._normalize_data(data)

                return DecisionResult.model_validate(normalized)

            except Exception as e:
                last_error = e

        raise ValueError(f"{self.name} failed after {retries} attempts: {last_error}")
