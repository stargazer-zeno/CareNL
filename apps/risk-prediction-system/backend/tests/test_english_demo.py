import json
from pathlib import Path

import pytest
from app.adapters.standard_adapter import StandardDataAdapter
from app.llm.prompt_builder import SFTPatternPromptBuilder, LLMPromptBuilder, sanitize_patient
from app.llm.llm_service import LLMService, parse_sft_pattern_response
from app.llm.basic_info_state_guard import correct_model_output
from app.llm.output_language import english_result, HAN
from app.config import LLMSettings
from app.aggregator import PredictionAggregator, flatten_for_csv

SAMPLES = Path(__file__).resolve().parents[2] / "frontend/public/samples"

@pytest.mark.parametrize("name", ["demo_full_probability.json", "demo_long_followup.json"])
def test_english_demo_through_adapter_and_both_prompts(name):
    sample = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    patient = StandardDataAdapter().from_json_obj(sample)[0]
    assert patient["basic_information"]["recipient_sex"] == "Male"
    assert patient["followup_series"]
    for builder in (SFTPatternPromptBuilder(), LLMPromptBuilder()):
        messages = builder.build_messages(patient)
        assert not HAN.search(json.dumps(messages, ensure_ascii=False))
        assert "English" in messages[0]["content"]
        assert "clinical_events:" in messages[1]["content"] or isinstance(builder, LLMPromptBuilder)


def test_english_outcome_fields_are_sanitized():
    original = {"true_labels":{"death":1}, "basic_information":{"recipient_sex":"Male","is_deceased":True,"cause_of_death":"infection"},
                "clinical_events":["Day 7: Stable liver function.", "Day 30: The patient died."]}
    clean = sanitize_patient(original)
    assert "true_labels" not in clean
    assert clean["basic_information"] == {"recipient_sex":"Male"}
    assert clean["clinical_events"] == ["Day 7: Stable liver function."]
    assert original["basic_information"]["is_deceased"] is True


def test_english_model_response_and_rationale(monkeypatch):
    service = LLMService(LLMSettings(base_url="http://model/v1",prompt_mode="sft_pattern_prob",rationale_second_pass=True))
    def chat(messages, **kwargs):
        assert not HAN.search(json.dumps(messages,ensure_ascii=False))
        if kwargs.get("response_format"):
            return '{"rationale":"Laboratory trends indicate improvement."}'
        return '<Pattern>ALT@improving + ALB@normal</Pattern><Analysis>Liver markers improved.</Analysis><Answer>{"1m":0.1,"1y":0.2,"5y":null}</Answer>'
    monkeypatch.setattr(service.client,"chat",chat)
    result = PredictionAggregator(service).predict_one({"id":"en", "basic_information":{}})
    assert result["llm"]["status"] == "ok"
    assert result["llm"]["rationale_source"] == "vllm_second_pass"
    assert result["llm"]["death_probability_5y"] is None
    assert not HAN.search(json.dumps(result,ensure_ascii=False))
    assert not HAN.search(json.dumps(flatten_for_csv(result),ensure_ascii=False))


def test_english_guard_does_not_introduce_chinese():
    text='<Pattern>recipient_sex@fluctuating + ALT@improving</Pattern><Analysis>recipient_sex fluctuated. ALT improved.</Analysis><Answer>{"1m":0.1,"1y":0.2,"5y":0.3}</Answer>'
    filtered=correct_model_output(text)
    assert filtered.removed_pattern_count == 1
    assert not HAN.search(filtered.text)
    assert 'recipient_sex' not in filtered.text
    assert parse_sft_pattern_response(filtered.text)["parse_status"] == "ok"
    only_baseline=correct_model_output('<Pattern>transplant_type@abnormal</Pattern><Analysis>Baseline observation.</Analysis>')
    assert only_baseline.placeholder_inserted
    assert not HAN.search(only_baseline.text)


def test_chinese_output_is_rejected_without_fabricating_translation():
    result=english_result({"status":"ok", "rationale":"\u4e2d\u6587", "death_probability_1m":0.2})
    assert result["status"] == "error"
    assert result["parse_status"] == "output_language_error"
    assert result["death_probability_1m"] is None
    assert not HAN.search(json.dumps(result,ensure_ascii=False))


def test_incomplete_feature_name_is_not_silently_accepted():
    parsed = parse_sft_pattern_response('<Pattern>N(@improving</Pattern><Analysis>Observed trend.</Analysis><Answer>{"1m":0.1,"1y":0.2,"5y":null}</Answer>')
    assert "unbalanced feature name" in "; ".join(parsed["parse_warnings"])


@pytest.mark.parametrize("changed_probability", [False, True])
def test_one_format_revision_preserves_probabilities(monkeypatch, changed_probability):
    svc = LLMService(LLMSettings(base_url="http://model/v1",prompt_mode="sft_pattern_prob",rationale_second_pass=False))
    original = '<Pattern>N(@improving)</Pattern><Analysis>Observed values.</Analysis><Answer>{"1m":0.1,"1y":0.2,"5y":null}</Answer>'
    revised = '<Pattern>N(%)@improving</Pattern><Analysis>Observed values.</Analysis><Answer>{"1m":0.1,"1y":0.2,"5y":null}</Answer>'
    if changed_probability:
        revised = revised.replace('"1m":0.1', '"1m":0.9')
    replies = iter([original, revised])
    calls = []
    def chat(messages, **kwargs):
        calls.append(messages)
        return next(replies)
    monkeypatch.setattr(svc.client, "chat", chat)
    result = svc.predict_one({"id":"repair", "basic_information":{}})
    assert len(calls) == 2
    assert result["death_probability_1m"] == 0.1
    assert bool(result["parse_warnings"]) is changed_probability
    assert result["patterns"][0]["pattern"] == ("N(@improving)" if changed_probability else "N(%)@improving")


@pytest.mark.parametrize("opening,closing", [("", ""), ("<Answer>", ""), ("", "</Answer>"), ("<Answer>", "</Answer>")])
def test_complete_untagged_answer_is_normalized_without_changing_probabilities(opening, closing):
    raw = '<Pattern>ALB@improving</Pattern><Analysis>Observed values increased.</Analysis> {"1m":0.12,"1y":0.23,"5y":null}'
    raw = raw.replace(' {', ' ' + opening + '{') + closing
    parsed = parse_sft_pattern_response(raw)
    assert parsed["pred_probs"] == {"1m":0.12,"1y":0.23,"5y":None}
    assert parsed["parse_status"] == "ok"
    assert parsed["parse_warnings"] == []


@pytest.mark.parametrize("suffix", [
    '{"1m":0.1,"1y":0.2}',
    '{"1m":0.1,"1y":0.2,"5y":1.5}',
    '{"1m":true,"1y":0.2,"5y":0.3}',
    '{"1m":0.1,"1m":0.4,"1y":0.2,"5y":0.3}',
    '{"1m":0.1,"1y":0.2,"5y":0.3} {"1m":0.4,"1y":0.5,"5y":0.6}',
    '{"1m":0.1,"1y":NaN,"5y":0.3}',
    '<Answer>{"1m":0.1,"1y":0.2,"5y":',
])
def test_uncertain_or_invalid_answer_is_not_silently_repaired(suffix):
    parsed = parse_sft_pattern_response('<Pattern>ALB@improving</Pattern><Analysis>Observed values.</Analysis>' + suffix)
    assert "missing <Answer> tag" in parsed["parse_warnings"]


def test_answer_normalization_does_not_hide_other_warnings():
    parsed = parse_sft_pattern_response('<Pattern>N(@improving</Pattern><Analysis>Observed values.</Analysis>{"1m":0.1,"1y":0.2,"5y":0.3}')
    assert "missing <Answer> tag" not in parsed["parse_warnings"]
    assert any("unbalanced feature name" in warning for warning in parsed["parse_warnings"])


@pytest.mark.parametrize("returned,expected", [(0.08,0.08),(None,None),(1.2,None),(-0.1,None),(True,None),("0.08",None)])
def test_missing_horizon_uses_only_valid_model_numbers(monkeypatch, returned, expected):
    svc = LLMService(LLMSettings(base_url="http://model/v1", retry_missing_probabilities=True))
    calls = []
    def chat(messages, **kwargs):
        calls.append((messages, kwargs))
        return json.dumps({"5y": returned})
    monkeypatch.setattr(svc.client, "chat", chat)
    probs = {"1m":0.012,"1y":0.031,"5y":None}
    valid = {"1m":True,"1y":True,"5y":True}
    svc._estimate_missing_horizons([{"role":"user","content":"Patient record"}], probs, valid)
    assert probs == {"1m":0.012,"1y":0.031,"5y":expected}
    assert len(calls) == 1
    assert calls[0][1]["response_format"]["json_schema"]["schema"]["required"] == ["5y"]


def test_complete_probabilities_do_not_trigger_extra_estimation(monkeypatch):
    svc = LLMService(LLMSettings(base_url="http://model/v1", retry_missing_probabilities=True))
    def chat(*args, **kwargs):
        raise AssertionError("No call expected")
    monkeypatch.setattr(svc.client,"chat",chat)
    svc._estimate_missing_horizons([], {"1m":0.01,"1y":0.02,"5y":0.03}, {})


def test_missing_horizon_request_failure_preserves_null(monkeypatch):
    from app.llm.llm_client import LLMClientError
    svc = LLMService(LLMSettings(base_url="http://model/v1", retry_missing_probabilities=True))
    def chat(*args, **kwargs):
        raise LLMClientError("offline")
    monkeypatch.setattr(svc.client,"chat",chat)
    probs={"1m":0.01,"1y":0.02,"5y":None}
    svc._estimate_missing_horizons([],probs,{})
    assert probs["5y"] is None
