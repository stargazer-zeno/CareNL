import React from "react";
import {
  displayRationale,
  formatProbability,
  normalizePatterns,
  resultStatusClass,
} from "../patterns.js";

function StatusTag({ status }) {
  return <span className={resultStatusClass(status)}>{status}</span>;
}

function hasDetails(llm) {
  return !!(
    llm?.patterns?.length ||
    llm?.pattern_output ||
    displayRationale(llm) ||
    llm?.parse_status ||
    llm?.parse_warnings?.length ||
    llm?.error
  );
}

export default function ResultsTable({ results, single = false }) {
  if (!results || results.length === 0) return null;
  return (
    <>
      {single ? (
        <div className="risk-summary">
          <div className="risk-summary-heading"><span>{results[0].id}</span><StatusTag status={results[0].llm?.status} /></div>
          <div className="risk-cards">
            {[["1 Month", "1m"], ["1 Year", "1y"], ["5 Years", "5y"]].map(([label, key]) => (
              <div className="risk-card" key={key}>
                <span>{label}</span>
                <strong>{formatProbability(results[0].llm?.[`death_probability_${key}`], { showNull: results[0].llm?.status === "ok" })}</strong>
                <small>Mortality risk</small>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="results">
            <caption className="sr-only">CareNL Prediction</caption>
            <thead><tr><th>ID</th><th>Status</th><th>1 Month</th><th>1 Year</th><th>5 Years</th><th>Pattern Count</th></tr></thead>
            <tbody>{results.map((r, i) => (
              <tr key={`${r.id || "row"}-${i}`}>
                <td className="id-col">{r.id}</td>
                <td><StatusTag status={r.llm?.status} /></td>
                {["1m", "1y", "5y"].map(key => <td key={key}>{formatProbability(r.llm?.[`death_probability_${key}`], { showNull: r.llm?.status === "ok" })}</td>)}
                <td>{r.llm?.pair_count ?? r.llm?.patterns?.length ?? "—"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      <div className="llm-detail-list">
        {results.filter((r) => hasDetails(r.llm)).map((r, i) => {
          const patterns = normalizePatterns(r.llm);
          const rationale = displayRationale(r.llm);
          return (
          <section className="llm-detail-card" key={`${r.id || i}-llm-detail`}>
            <div className="llm-detail-header">
              <div>
                <span className="detail-label">CareNL Pattern Analysis</span>
                <span className="id-col">{r.id || `row_${i + 1}`}</span>
              </div>
              <div className="detail-statuses">
                <StatusTag status={r.llm?.status} />
                {r.llm?.parse_status && (
                  <span className="parse-status">
                    Parse status: {r.llm.parse_status}
                  </span>
                )}
              </div>
            </div>

            {patterns.length > 0 && (
              <div className="pattern-list">
                {patterns.map((item, idx) => (
                  <div className="pattern-item" key={`${r.id || i}-pattern-${idx}`}>
                    <div className="pattern-index">Pattern {idx + 1}</div>
                    <div className="pattern-content">
                      <div className="pattern-title">{item.pattern || "Pattern name unavailable"}</div>
                      {item.analysis && (
                        <div className="pattern-analysis">
                          <span className="analysis-label">Clinical Analysis</span>
                          {item.analysis}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {patterns.length === 0 && r.llm?.pattern_output && (
              <pre className="pattern-raw">{r.llm.pattern_output}</pre>
            )}

            {rationale && (
              <div className="answer-text">
                <strong>Overall Rationale:</strong>
                <span>{rationale}</span>
              </div>
            )}

            {r.llm?.parse_warnings?.length > 0 && (
              <div className="warnings">
                <strong>Parse Warnings:</strong>{r.llm.parse_warnings.join("; ")}
              </div>
            )}

            {r.llm?.error && <div className="error">Prediction error: {r.llm.error}</div>}
          </section>
          );
        })}
      </div>
    </>
  );
}
