from __future__ import annotations

import json
from typing import Any

from .llm.llm_service import LLMService
from .llm.output_language import english_result


class PredictionAggregator:
    """Run CareNL predictions using the configured LLM only."""

    def __init__(self, llm: LLMService):
        self.llm = llm

    @staticmethod
    def _patient_id(patient: dict[str, Any], index: int) -> str:
        pid = patient.get("id")
        if pid is None or str(pid).strip() == "":
            return f"row_{index + 1}"
        return str(pid)

    def predict_batch(self, patients: list[dict[str, Any]]) -> list[dict[str, Any]]:
        llm_results = self.llm.predict_batch(patients)

        combined: list[dict[str, Any]] = []
        for index, patient in enumerate(patients):
            combined.append(
                {
                    "id": self._patient_id(patient, index),
                    "llm": english_result(llm_results[index]),
                }
            )
        return combined

    def predict_one(self, patient: dict[str, Any]) -> dict[str, Any]:
        return self.predict_batch([patient])[0]


def flatten_for_csv(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten one combined result into a single CSV-friendly row."""
    llm = result.get("llm", {}) or {}

    def llm_probability(field: str) -> Any:
        value = llm.get(field)
        if value is None and llm.get("status") == "ok":
            return "null"
        return value

    return {
        "id": result.get("id"),
        "llm_status": llm.get("status"),
        "llm_death_probability_1m": llm_probability("death_probability_1m"),
        "llm_death_probability_1y": llm_probability("death_probability_1y"),
        "llm_death_probability_5y": llm_probability("death_probability_5y"),
        "llm_rationale": llm.get("rationale"),
        "llm_rationale_source": llm.get("rationale_source"),
        "llm_pattern_output": llm.get("pattern_output"),
        "llm_patterns": json.dumps(llm.get("patterns") or [], ensure_ascii=False),
        "llm_pair_count": llm.get("pair_count"),
        "llm_parse_status": llm.get("parse_status"),
        "llm_parse_warnings": "; ".join(llm.get("parse_warnings") or []),
        "llm_error": llm.get("error"),
    }
