import React, { useCallback, useEffect, useRef, useState } from "react";
import HealthBar from "./components/HealthBar.jsx";
import ResultsTable from "./components/ResultsTable.jsx";
import {
  createJob,
  downloadUrl,
  getHealth,
  getJob,
  getJobResults,
  predictOne,
} from "./api.js";

const SAMPLE_URL = "/samples/demo_long_followup.json";

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");

  const [jsonText, setJsonText] = useState("");
  const [singleResult, setSingleResult] = useState(null);
  const [singleError, setSingleError] = useState("");
  const [singleBusy, setSingleBusy] = useState(false);
  const jsonInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [batchError, setBatchError] = useState("");
  const [batchBusy, setBatchBusy] = useState(false);

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await getHealth());
      setHealthError("");
    } catch (e) {
      setHealthError(e.message);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  async function handleSingle() {
    if (!jsonText.trim()) {
      setSingleError('Paste a standard patient JSON record or select "Load sample".');
      jsonInputRef.current?.focus();
      return;
    }
    setSingleBusy(true);
    setSingleError("");
    setSingleResult(null);
    try {
      const patient = JSON.parse(jsonText);
      const res = await predictOne(patient);
      setSingleResult(res);
    } catch (e) {
      setSingleError(e.message);
    } finally {
      setSingleBusy(false);
    }
  }

  async function handleLoadSample() {
    setSingleError("");
    try {
      const response = await fetch(SAMPLE_URL, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const sample = await response.json();
      setJsonText(JSON.stringify(sample, null, 2));
    } catch (e) {
      setSingleError(`Unable to load the sample data: ${e.message}`);
      return;
    }
    setSingleResult(null);
    requestAnimationFrame(() => {
      jsonInputRef.current?.focus();
      jsonInputRef.current?.setSelectionRange(0, 0);
    });
  }

  function handleClearSingle() {
    setJsonText("");
    setSingleResult(null);
    setSingleError("");
    jsonInputRef.current?.focus();
  }

  // Poll a job until it finishes.
  useEffect(() => {
    if (!job || ["completed", "failed"].includes(job.status)) return;
    const timer = setInterval(async () => {
      try {
        const meta = await getJob(job.job_id);
        setJob(meta);
        if (meta.status === "completed") {
          const r = await getJobResults(job.job_id);
          setBatchResults(r.results);
        }
      } catch (e) {
        setBatchError(e.message);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [job]);

  async function handleUpload() {
    if (!file) {
      setBatchError("Select a file before starting the prediction.");
      return;
    }
    setBatchBusy(true);
    setBatchError("");
    setBatchResults(null);
    setJob(null);
    try {
      const meta = await createJob(file);
      setJob(meta);
    } catch (e) {
      setBatchError(e.message);
    } finally {
      setBatchBusy(false);
    }
  }

  const singleRows = singleResult ? [singleResult] : null;
  const progress =
    job?.total > 0 ? Math.min(100, Math.round((job.completed / job.total) * 100)) : 0;

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-copy">
          <div className="eyebrow">PEDIATRIC LIVER TRANSPLANT · RISK PREDICTION SYSTEM</div>
          <h1>CareNL</h1>
          <p className="brand-tagline">Care New Liver, Care New Life</p>
          <p className="subtitle">
            Predict post-transplant mortality risk from longitudinal patient records with interpretable pattern analysis.
          </p>
          <div className="hero-tags">
            <span>Longitudinal risk prediction</span>
            <span>Interpretable patterns</span>
            <span>Batch assessment</span>
          </div>
        </div>
        <div className="hero-horizons" aria-label="Prediction horizons">
          <span className="horizon-label">Prediction horizons</span>
          <div className="horizon-times"><span><strong>1</strong>Month</span><span><strong>1</strong>Year</span><span><strong>5</strong>Years</span></div>
          <p>Post-transplant mortality risk</p>
        </div>
      </header>

      <HealthBar health={health} error={healthError} onRefresh={refreshHealth} />

      <main>
        <section className="card workspace-card">
          <div className="section-heading">
            <div className="section-number">01</div>
            <div>
              <h2>Single-Patient Prediction</h2>
              <p>Paste one standard patient JSON record to generate a CareNL prediction.</p>
            </div>
          </div>

          <div className="editor-shell">
            <div className="editor-toolbar">
              <span className="editor-title">Patient Data · JSON</span>
              <span className="editor-meta">
                {jsonText.trim() ? `${jsonText.length} characters` : "Waiting for input"}
              </span>
            </div>
            <textarea
              ref={jsonInputRef}
              aria-label="Standard patient JSON"
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
              }}
              rows={12}
              spellCheck={false}
              placeholder={'Paste a standard patient JSON record here, or select "Load sample" below...'}
            />
          </div>

          <div className="action-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSingle}
              disabled={singleBusy}
            >
              {singleBusy ? <span className="spinner" aria-hidden="true" /> : null}
              {singleBusy ? "Analyzing..." : "Run prediction"}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleLoadSample}>
              Load sample
            </button>
            {jsonText && (
              <button type="button" className="btn btn-text" onClick={handleClearSingle}>
                Clear
              </button>
            )}
          </div>
          {singleError && <p className="notice error-notice">{singleError}</p>}

          {singleResult && (
            <div className="result-section">
              <div className="result-heading">
                <span>CareNL Prediction</span>
                <small>Mortality risk and interpretable pattern analysis</small>
              </div>
              <ResultsTable results={singleRows} single />
            </div>
          )}
        </section>

        <section className="card workspace-card">
          <div className="section-heading">
            <div className="section-number">02</div>
            <div>
              <h2>Batch Prediction</h2>
              <p>Upload a patient data file to process it asynchronously and generate downloadable structured results.</p>
            </div>
          </div>

          <label className="upload-zone">
            <input
              type="file"
              accept=".json,.jsonl,.csv,.xlsx,.xls"
              onChange={(e) => {
                setFile(e.target.files[0] || null);
                setBatchError("");
              }}
            />
            <span className="upload-icon" aria-hidden="true">↑</span>
            <span className="upload-copy">
              <strong>{file ? file.name : "Select a patient data file"}</strong>
              <small>
                {file
                  ? `${(file.size / 1024).toFixed(1)} KB`
                  : "Supports JSON, JSONL, CSV, and XLSX, with one patient per record"}
              </small>
            </span>
            <span className="upload-action">{file ? "Choose another" : "Browse files"}</span>
          </label>

          <div className="action-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={batchBusy || !file}
            >
              {batchBusy ? <span className="spinner" aria-hidden="true" /> : null}
              {batchBusy ? "Creating job..." : "Upload and predict"}
            </button>
            {file && <span className="selection-note">Selected: {file.name}</span>}
          </div>

          {job && (
            <div className="job-status">
              <div className="job-status-header">
                <div>
                  <span className="job-label">Job ID</span>
                  <code>{job.job_id}</code>
                </div>
                <span className={`job-state job-state-${job.status}`}>{job.status}</span>
              </div>
              <div className="progress-info">
                <span>Processing progress</span>
                <strong>{job.completed}/{job.total}</strong>
              </div>
              <div
                className="progress-track"
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <span style={{ width: `${progress}%` }} />
              </div>
              {job.failed ? <div className="failed-note">Failed records: {job.failed}</div> : null}
              {job.status === "completed" && (
                <div className="download-row">
                  <a className="btn btn-download" href={downloadUrl(job.job_id, "csv")}>
                    Download CSV
                  </a>
                  <a className="btn btn-download" href={downloadUrl(job.job_id, "json")}>
                    Download JSON
                  </a>
                </div>
              )}
            </div>
          )}
          {batchError && <p className="notice error-notice">{batchError}</p>}
          {batchResults && (
            <div className="result-section">
              <div className="result-heading">
                <span>CareNL Batch Predictions</span>
                <small>{batchResults.length} records</small>
              </div>
              <ResultsTable results={batchResults} />
            </div>
          )}
        </section>
      </main>

      <footer>
        <span>CareNL Prediction System</span>
        <span className="footer-divider">·</span>
        <span>For research demonstration only. Not for clinical decision-making.</span>
      </footer>
    </div>
  );
}
