from __future__ import annotations

import copy
import json
from typing import Any

# Fields that directly leak the mortality outcome must never reach the LLM.
LEAKAGE_TOP_LEVEL = {"真实标签", "true_labels", "outcome_labels", "labels"}
LEAKAGE_BASE_FIELDS = {"是否死亡", "死亡时间", "死亡原因", "is_deceased", "death_time", "cause_of_death", "death_date", "mortality_outcome"}
CLINICAL_EVENTS_FIELD = "临床事件"
EVENT_LEAKAGE_TERMS = (
    "死亡",
    "去世",
    "病故",
    "生存结局",
    "存活结局",
    "结局标签",
    "终点标签",
    "mortality",
    "deceased",
    "died",
    "death",
)

SYSTEM_PROMPT = """You are an experienced pediatric liver transplant follow-up specialist.
Using only the supplied baseline information, longitudinal laboratory results, medications and historical clinical events, estimate mortality risk within 1 month, 1 year and 5 years AFTER the latest follow-up time point.
Do not invent patient facts. Write all narrative content in English only, including feature names, analyses and rationale. Do not output Chinese characters.
Return only a strict JSON object, without Markdown or additional commentary:
{"death_probability_1m": <probability from 0 to 1 or null>, "death_probability_1y": <probability from 0 to 1 or null>, "death_probability_5y": <probability from 0 to 1 or null>, "rationale": "<brief English clinical rationale, at most 100 words>"}
Use null when a probability cannot be estimated; do not invent a value."""

SFT_SYSTEM_PROMPT = "You are a helpful assistant. Respond in English only. Do not output Chinese characters."

SFT_USER_PREFIX_TEMPLATE = """You are an experienced pediatric liver transplant physician.

### Task
Use the complete patient history up to the latest follow-up time point. First identify the key clinical patterns observed up to that point, then prospectively estimate mortality risk over the NEXT 1 month, 1 year and 5 years. Use only the supplied facts.
All three horizons start at the LAST recorded follow-up, not at transplantation. A record that already spans five years still requires a prospective five-year estimate from its last observation. Absence of future observed outcomes is expected in prediction and is not, by itself, a reason to return null. Provide a model-estimated number for each horizon when supported; use null only when you cannot make a supportable estimate.
--------------------------------------------------
{SUMMARY_TEXT}
### Patient record"""

SFT_OUTPUT_INSTRUCTIONS = """### Output instructions
Write exclusively in English. Use English feature names, English trend labels and English analyses. Do not include Chinese text or Markdown.
Return only the following sequence of tags:
1. For each clinical pattern, output:
   <Pattern>feature_a@trend_x + feature_b@trend_y</Pattern>
   <Analysis>English clinical analysis of this pattern</Analysis>
2. Allowed trend labels are exactly: worsening, abnormal, fluctuating, sudden_abnormality, improving, normal.
3. Base dynamic patterns on longitudinal observations. Do not describe static baseline fields such as sex, blood group, transplant type or diagnosis as fluctuating laboratory measurements.
4. After all patterns, append:
   <Answer>{"1m": <probability>, "1y": <probability>, "5y": <probability>}</Answer>
   Each probability is a number from 0.0 to 1.0, or null if it cannot be estimated. Do not invent missing probabilities.
5. A probability above 0.5 indicates greater predicted mortality risk than survival for that horizon; below 0.5 indicates greater predicted survival probability.
6. For a rich longitudinal record, aim for 4-6 DISTINCT evidence-supported patterns, each in its own <Pattern>/<Analysis> pair. Use fewer only when the record genuinely lacks evidence. Never pad or duplicate patterns to meet a count.
7. Each pattern should contain only 1-3 closely related features. Do not merge all laboratory markers into one pattern. Review separate domains when supported: hepatocellular injury (ALT/AST), cholestasis (TB/DB/GGT), synthetic/coagulation function (ALB/INR/PT), blood counts, renal observations, and medication exposure. Select the domains supported by this patient's actual data, not a fixed checklist.
8. Each Analysis must cite at least two supplied numeric observations and their postoperative days where aligned time points are available. Distinguish early recovery, any later transient changes, and the latest follow-up state. Do not call every series improving or claim monotonic improvement when intermediate reversals exist.
9. Copy feature names exactly from the record, including punctuation: for example N(%)@fluctuating, not N(@fluctuating). Keep brackets and parentheses inside the feature name, before @. Trend labels must match the allowed labels exactly, with no trailing punctuation.
10. Do not infer normal ranges, units, adherence, absence of infection, or absence of complications from laboratory trends alone. Use documented clinical events for such claims; otherwise describe only observed numerical trajectories. Missing values are not normal values.
Format example (illustrative placeholders, not patient findings):
<Pattern>feature_a@worsening + feature_b@abnormal</Pattern><Analysis>English explanation based on the supplied observations.</Analysis><Answer>{"1m": p_1m, "1y": p_1y, "5y": p_5y}</Answer>
Here p_1m, p_1y and p_5y are placeholders: replace them with your independently estimated numeric probabilities or null. Never copy illustrative values.
"""

def _event_contains_leakage(event: Any) -> bool:
    if isinstance(event, str):
        text = event
    else:
        try:
            text = json.dumps(event, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            text = str(event)
    normalized = "".join(text.lower().split())
    return any(term.lower() in normalized for term in EVENT_LEAKAGE_TERMS)


def _sanitize_clinical_events(events: Any) -> list[Any] | None:
    """Keep useful historical events while conservatively dropping outcome leaks."""
    if not isinstance(events, list):
        return None

    safe_events: list[Any] = []
    for event in events:
        if isinstance(event, str):
            if not event.strip() or _event_contains_leakage(event):
                continue
            safe_events.append(event)
        elif isinstance(event, dict):
            if not event or _event_contains_leakage(event):
                continue
            safe_events.append(event)
    return safe_events


def sanitize_patient(patient: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with mortality-leaking fields and events removed."""
    cleaned = copy.deepcopy(patient)
    for key in LEAKAGE_TOP_LEVEL:
        cleaned.pop(key, None)
    for section in ("基础信息", "basic_information"):
        base = cleaned.get(section)
        if isinstance(base, dict):
            for field in LEAKAGE_BASE_FIELDS:
                base.pop(field, None)
    for section in (CLINICAL_EVENTS_FIELD, "clinical_events"):
        if section in cleaned:
            safe_events = _sanitize_clinical_events(cleaned[section])
            if safe_events is None:
                cleaned.pop(section, None)
            else:
                cleaned[section] = safe_events
    return cleaned


def _section_count(patient: dict[str, Any], section: str) -> int:
    value = patient.get(section)
    return len(value) if isinstance(value, list) else 0


def build_summary_text(patient: dict[str, Any]) -> str:
    """Create a deterministic brief summary for the SFT evaluation prompt."""
    cleaned = sanitize_patient(patient)
    base = cleaned.get("basic_information", cleaned.get("基础信息", {})) or {}
    if not isinstance(base, dict):
        base = {}
    base_parts = [f"{key}: {value}" for key, value in list(base.items())[:16] if str(value).strip()]
    counts = []
    for english, legacy in (("followup_series", "时序随访基础信息"),
                            ("laboratory_series", "时序检验指标 (纯数值序列)"),
                            ("medication_series", "时序用药记录 (纯数值序列)"),
                            ("clinical_events", CLINICAL_EVENTS_FIELD)):
        section = english if english in cleaned else legacy
        counts.append(f"{english}: {_section_count(cleaned, section)}")
    return (f"Patient ID: {cleaned.get('id', 'unknown')}\n"
            f"Baseline summary: {'; '.join(base_parts) if base_parts else 'Not provided'}\n"
            f"Longitudinal record summary: {'; '.join(counts)}")



class LLMPromptBuilder:
    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self.system_prompt = system_prompt

    def build_user_content(self, patient: dict[str, Any]) -> str:
        cleaned = sanitize_patient(patient)
        body = json.dumps(cleaned, ensure_ascii=False, indent=2)
        return (
            "Patient data through the latest follow-up (outcome labels removed):\n\n"
            f"{body}\n\n"
            "Estimate mortality risk over the next 1 month, 1 year and 5 years. "
            "Return strict JSON as specified in the system instructions, with all narrative content in English."
        )

    def build_messages(self, patient: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.build_user_content(patient)},
        ]


class SFTPatternPromptBuilder:
    """Build prompts for the SFT model used by basic_test_sft_pattern_prob.py."""

    def __init__(self, system_prompt: str = SFT_SYSTEM_PROMPT):
        self.system_prompt = system_prompt

    def build_user_content(self, patient: dict[str, Any]) -> str:
        cleaned = sanitize_patient(patient)
        summary_text = build_summary_text(cleaned)
        clean_ehr = json.dumps(cleaned, ensure_ascii=False, indent=2)
        prefix = SFT_USER_PREFIX_TEMPLATE.replace("{SUMMARY_TEXT}", summary_text)
        return f"{prefix}\n{clean_ehr}\n\n{SFT_OUTPUT_INSTRUCTIONS}"

    def build_messages(self, patient: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.build_user_content(patient)},
        ]


def build_prompt_builder(prompt_mode: str):
    if prompt_mode == "sft_pattern_prob":
        return SFTPatternPromptBuilder()
    if prompt_mode in {"", "generic_json"}:
        return LLMPromptBuilder()
    raise ValueError(
        f"Unsupported LLM_PROMPT_MODE={prompt_mode!r}; use sft_pattern_prob or generic_json."
    )
