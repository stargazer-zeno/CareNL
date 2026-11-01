# CareNL Prediction System

[中文说明](README.zh-CN.md)

Browser-based research system for pediatric liver transplantation follow-up mortality-risk prediction. It accepts standard longitudinal records and uses CareNL LLM predictions for 1 month, 1 year, and 5 years.

> Research demonstration only. Not for diagnosis, treatment, prognosis communication, or clinical decision-making.

## Architecture

```text
React/nginx -> FastAPI -> input adapter
                         └─ OpenAI-compatible LLM API
```

CareNL calls only the configured LLM. Explicit `null` results are preserved, and partial results are never completed with another model. Archived ML source and artifacts remain in the repository but are not loaded or packaged in the runtime image.

## Docker deployment

### External LLM service

```bash
cp .env.example .env
docker compose up -d --build
```

- Web UI: <http://localhost:8080>
- Backend API: <http://localhost:8000>
- API documentation: <http://localhost:8000/docs>

For an external OpenAI-compatible service, configure:

```dotenv
LLM_BASE_URL=https://your-vllm-host.example/v1
LLM_API_KEY=EMPTY
LLM_MODEL_NAME=zeno156/PediLT-Risk-Qwen3-4B
LLM_PROMPT_MODE=sft_pattern_prob
```

Set `LLM_BASE_URL` and the exact served `LLM_MODEL_NAME` before predicting. A blank URL disables prediction; the application still starts. `/health` is application liveness, while `/api/health` also checks remote connectivity and model availability. Host ports can be set with `FRONTEND_PORT` and `BACKEND_PORT`; the current local deployment uses 18080 and 18000.

### Optional local vLLM profile

Requirements: Linux Docker host, NVIDIA driver, NVIDIA Container Toolkit, and sufficient GPU memory for the selected context length.

```bash
# Set HF_TOKEN only when the Hugging Face repository requires authentication.
export HF_TOKEN="replace-with-hugging-face-token"
docker compose -f compose.yaml -f compose.vllm.yaml --profile llm up -d --build
```

The local OpenAI-compatible vLLM endpoint is exposed at <http://localhost:8001/v1>. Adjust `VLLM_MAX_MODEL_LEN` and `VLLM_TENSOR_PARALLEL_SIZE` for the available hardware.

## Input formats

- `.json`: one patient object, an array, or `{ "patients": [...] }`
- `.jsonl`: one patient object per line
- `.csv` / `.xlsx`: one patient per row; a `patient_json` column may contain the complete JSON record

Two explicitly synthetic JSON examples are available under `frontend/public/samples/`. They contain no real identity, outcome label, or exact clinical date.

## Main API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Application and CareNL prediction status |
| `POST` | `/api/predict` | One-patient CareNL prediction |
| `POST` | `/api/batch_predict` | Batch prediction from JSON |
| `POST` | `/api/jobs` | Asynchronous file upload job |
| `GET` | `/api/jobs/{job_id}` | Job status |
| `GET` | `/api/jobs/{job_id}/results` | Job results |
| `GET` | `/api/jobs/{job_id}/download` | CSV or JSON download |

Uploaded files and results are stored only in the local Docker volume. Do not expose this research service to untrusted networks without authentication, TLS, access control, retention controls, and an institutional privacy review.

## Local development and tests

```powershell
./scripts/run_backend.ps1
./scripts/run_frontend.ps1
```

```bash
cd backend
python -m pytest

cd ../frontend
npm ci
npm test
npm run build
```

## LLM-only API migration

Prediction objects now contain `{ "id": "...", "llm": { ... } }`; the `ml` field is removed. Batch responses retain `{ "count", "results" }`. `/predict` and `/batch_predict` return HTTP 410 with migration instructions; use their `/api/` equivalents.

CSV exports retain `id` and `llm_*` columns only. Historical job files are preserved unchanged; result reads and downloads project the stored LLM branch without recomputation. `completed` counts processed records; `failed` counts `error`, `disabled`, or missing results, while `partial` is a processed partial success. A completed job may contain failed records: inspect each result status.

The application tests run without local ML artifacts or XGBoost dependencies. Archived artifact tests are skipped unless optional `xgboost==3.2.0` and `scikit-learn` are installed with the historical artifacts available.

## English demonstration and output

The two `frontend/public/samples/` records use English field names and values: `basic_information`, `followup_series`, `laboratory_series`, `medication_series`, and optional `clinical_events`. Measurements and time-series order are unchanged. Missing numeric values remain `NaN` inside series strings. Legacy Chinese input sections are still accepted; do not supply both English and Chinese aliases for the same section.

Both prediction prompts and the second-pass rationale prompt request English only. Tagged predictions retain `<Pattern>`, `<Analysis>` and `<Answer>` with `1m`, `1y`, `5y` probabilities. English trends are `worsening`, `abnormal`, `fluctuating`, `sudden_abnormality`, `improving`, and `normal`.

If a model still returns Chinese text, the API returns `output_language_error` instead of displaying or exporting that text as a valid prediction. Historical Chinese results are likewise hidden on read, without modifying stored originals. This is a language check, not an automatic translation or a guarantee of clinical accuracy. Real English-generation behavior must be tested after the remote model is running.

### Missing-horizon estimates

With `LLM_RETRY_MISSING_PROBABILITIES=true` (Compose default), the tagged prediction flow asks the same model once more about null/missing horizons, using the original patient record. Only finite numeric responses in [0,1] are accepted; existing numeric horizons are unchanged. The rationale is generated after this step. Failed or unsupported estimates remain null. No fixed value, other-model result or cross-horizon interpolation is used. Set this option to false to preserve first-pass nulls without another request. This may add one model request and does not establish calibration or clinical validity.
