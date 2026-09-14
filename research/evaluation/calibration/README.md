# Probability calibration results

[中文说明](README.zh-CN.md)

This directory contains the manuscript-aligned aggregate probability-calibration results for the fixed XGBoost and CareNL-LLM models. Platt scaling is the primary calibration method, and isotonic regression is the sensitivity analysis. The released material contains aggregate tables, manuscript figures, and Platt coefficients only. It contains no EHR data, patient-level predictions, patient assignments, source manifests, model serializations, or clinical deployment configuration.

The fixed patient split was created from 1,181 test-set patient IDs: IDs were sorted lexicographically, permuted once with NumPy `default_rng(seed=42)`, and divided into 392 calibration patients and 789 evaluation patients. Follow-up eligibility produces the horizon-specific counts reported in `results/tables/calibration_split.csv`. The split was shared by both models and all horizons.

## Public contents

- `parameters/platt_parameters.json`: XGBoost Platt coefficients in the existing compatibility structure.
- `results/tables/platt_parameters.csv`: XGBoost and CareNL-LLM Platt coefficients and calibration-sample counts.
- `results/tables/overall.csv`: AUROC, AUPRC, and Brier score results.
- `results/tables/calibration.csv`: calibration diagnostics.
- `results/tables/paired.csv`: paired Brier-score changes from raw to Platt-calibrated probabilities.
- `results/tables/dca_summary.csv`: decision-curve summaries.
- `results/tables/locked_operating_points.csv`: locked-threshold diagnostic and net-benefit results.
- `results/figures/`: manuscript calibration and decision-curve figures.
- `CALIBRATION_PROTOCOL.md` and `RESULTS.md`: released design and result summaries.

## Analysis utilities

`run_calibration_analysis.py`, `verify_calibration_outputs.py`, and `calibration_common.py` are retained analysis utilities that require authorized private inputs. They are not modified by this data release and do not contain the private fixed patient assignment. The manuscript-aligned CSV files and figures in this directory are the authoritative public aggregate results.

## Scope and limitations

The reported evaluation is internal and patient-disjoint, not an external validation. The models were not retrained. The coefficients and locked study thresholds are tied to the fixed models, source predictions, outcome definitions, and study cohort. They are not loaded by `apps/risk-prediction-system` and are not clinical deployment recommendations. Prospective use requires independent validation, governance approval, and local recalibration.
