import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Isolate API tests from live inference and persistent deployment jobs.
import os
import tempfile
import pytest
os.environ["LLM_BASE_URL"] = ""
os.environ["JOBS_DIR"] = tempfile.mkdtemp(prefix="carenl-tests-")

@pytest.fixture(autouse=True)
def isolated_api_jobs(tmp_path, monkeypatch):
    import sys
    module = sys.modules.get("app.main")
    if module is not None:
        monkeypatch.setattr(module.job_store, "jobs_dir", tmp_path)
