"""Keep model-generated Chinese text out of the English application contract."""
import json
import re
from typing import Any

HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U000323af]")


def english_result(result: dict[str, Any]) -> dict[str, Any]:
    if not HAN.search(json.dumps(result, ensure_ascii=False)):
        return result
    return {
        "status": "error",
        "death_probability_1m": None,
        "death_probability_1y": None,
        "death_probability_5y": None,
        "patterns": [], "pattern_output": "", "pair_count": 0,
        "rationale": None, "rationale_source": None,
        "parse_status": "output_language_error", "parse_warnings": [],
        "error": "The model returned Chinese text despite the English-only instructions. No prediction is displayed. Retry with an English-capable model or review its language configuration.",
    }
