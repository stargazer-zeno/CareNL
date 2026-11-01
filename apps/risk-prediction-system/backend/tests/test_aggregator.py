from app.aggregator import PredictionAggregator, flatten_for_csv


class FakeLLMService:
    def __init__(self):
        self.calls = []

    def predict_batch(self, patients):
        self.calls.append(patients)
        return [
            {
                "status": "ok",
                "death_probability_1m": 0.0129,
                "death_probability_1y": None,
                "death_probability_5y": None,
                "rationale": "Overall risk rationale",
                "rationale_source": "vllm_second_pass",
                "patterns": [],
                "parse_status": "ok",
                "parse_warnings": [],
                "error": None,
            }
            for _ in patients
        ]


def test_aggregator_uses_only_llm_and_preserves_null():
    llm = FakeLLMService()
    aggregator = PredictionAggregator(llm)
    result = aggregator.predict_one({"id": "patient_1"})
    assert len(llm.calls) == 1
    assert set(result) == {"id", "llm"}
    assert result["llm"]["death_probability_1y"] is None
    row = flatten_for_csv(result)
    assert row["llm_death_probability_1y"] == "null"
    assert row["llm_death_probability_5y"] == "null"
    assert row["llm_rationale"] == "Overall risk rationale"
    assert row["llm_rationale_source"] == "vllm_second_pass"
    assert row["llm_parse_status"] == "ok"
    for hidden_column in (
        "llm_native_probability_1m",
        "llm_probability_source_1y",
        "llm_fallback_fields",
        "llm_answer_text",
        "llm_native_parse_status",
    ):
        assert hidden_column not in row


def test_csv_leaves_non_model_null_probabilities_empty():
    result = {
        "id": "patient_1",
        "ml": {"status": "ok"},
        "llm": {
            "status": "error",
            "death_probability_1m": None,
            "death_probability_1y": None,
            "death_probability_5y": None,
        },
    }

    row = flatten_for_csv(result)

    assert row["llm_death_probability_1m"] is None
    assert row["llm_death_probability_1y"] is None
    assert row["llm_death_probability_5y"] is None
