import json
import sys
from pathlib import Path

import httpx
import pytest
from app.config import LLMSettings
from app.llm.llm_client import LLMClient
from app.jobs.store import JobStore
from app.main import app, job_store
from fastapi.testclient import TestClient

@pytest.mark.parametrize("code,ids,ready,reachable", [(200,["expected"],True,True),(200,["other"],False,True),(401,[],False,False),(503,[],False,False)])
def test_model_health(monkeypatch, code, ids, ready, reachable):
    def get(self, url, **kwargs):
        return httpx.Response(code, json={"data":[{"id":i} for i in ids]}, request=httpx.Request("GET",url))
    monkeypatch.setattr(httpx.Client,"get",get)
    result=LLMClient(LLMSettings(base_url="http://model/v1", model_name="expected")).ping()
    assert result["ready"] is ready
    assert result["reachable"] is reachable


def test_model_unreachable(monkeypatch):
    def get(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(httpx.Client,"get",get)
    assert LLMClient(LLMSettings(base_url="http://model/v1")).ping()["ready"] is False


def test_application_does_not_import_ml():
    assert "app.ml.ml_service" not in sys.modules


def test_historical_download_projection_keeps_originals(tmp_path):
    folder=tmp_path/"historical"; folder.mkdir()
    result=[{"id":"old", "ml":{"status":"ok","death_probability_1m":0.9}, "llm":{"status":"ok","death_probability_1m":0.1,"death_probability_1y":None}}]
    original=json.dumps(result)
    (folder/"results.json").write_text(original)
    (folder/"results.csv").write_text("original archive")
    (folder/"meta.json").write_text(json.dumps({"job_id":"historical","status":"completed","total":1}))
    with TestClient(app) as client:
        read=client.get("/api/jobs/historical/results")
        assert set(read.json()["results"][0])=={"id","llm"}
        exported=client.get("/api/jobs/historical/download?format=json")
        assert set(exported.json()[0])=={"id","llm"}
        csv=client.get("/api/jobs/historical/download?format=csv").text
        assert "ml_status" not in csv.replace("llm_status", "")
        assert "null" in csv
    assert (folder/"results.json").read_text()==original
    assert (folder/"results.csv").read_text()=="original archive"


def test_batch_failure_count_and_partial(tmp_path):
    store=JobStore(tmp_path)
    folder=tmp_path/"counts"; folder.mkdir()
    (folder/"meta.json").write_text(json.dumps({"job_id":"counts"}))
    statuses=["ok","partial","error","disabled"]
    store._run_job("counts", [{}]*4, lambda patients:[{"id":str(i),"llm":{"status":status}} for i,status in enumerate(statuses)])
    meta=store.get_status("counts")
    assert meta["completed"]==4
    assert meta["failed"]==2
    assert meta["status"]=="completed"
    store.shutdown()
