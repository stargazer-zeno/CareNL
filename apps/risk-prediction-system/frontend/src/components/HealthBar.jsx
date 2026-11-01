import React from "react";

export default function HealthBar({ health, error, onRefresh }) {
  const prediction = health?.llm;
  const appReady = !!health && !error;
  const ready = appReady && prediction?.ready === true;
  const note = !appReady ? "Status unavailable" : !prediction?.enabled ? "Not configured"
    : !prediction?.reachable ? "Unreachable" : !prediction?.model_available ? "Model unavailable" : "Ready";
  return (
    <div className="healthbar" role="status">
      <div className="health-item"><span className={`dot ${appReady ? "dot-ok" : "dot-bad"}`} />Application <span className="health-note">({appReady ? "Ready" : "Unavailable"})</span></div>
      <div className="health-item" title={prediction?.reason || ""}><span className={`dot ${ready ? "dot-ok" : "dot-bad"}`} />CareNL <span className="health-note">({note})</span></div>
      <button className="btn-small" onClick={onRefresh}>Refresh status</button>
      {error && <span className="health-error">{error}</span>}
    </div>
  );
}
