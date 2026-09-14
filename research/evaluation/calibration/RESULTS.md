# Reported aggregate results

The released tables and figures report the fixed patient-disjoint calibration experiment described in `CALIBRATION_PROTOCOL.md`. The base XGBoost and CareNL-LLM models were unchanged. Both models used the same 392-patient calibration split and 789-patient evaluation split, with horizon-specific eligibility recorded in `results/tables/calibration_split.csv`.

| Model | Horizon | Raw Brier score | Platt Brier score | Paired change (Platt - raw) |
|---|---:|---:|---:|---:|
| XGBoost | 1 month | 0.04085 | 0.00582 | -0.035038 |
| XGBoost | 1 year | 0.08162 | 0.02085 | -0.060765 |
| XGBoost | 5 years | 0.12044 | 0.04933 | -0.071112 |
| CareNL-LLM | 1 month | 0.01309 | 0.00580 | -0.007292 |
| CareNL-LLM | 1 year | 0.03778 | 0.02089 | -0.016893 |
| CareNL-LLM | 5 years | 0.07351 | 0.04953 | -0.023977 |

Platt scaling preserved rank order. Raw and Platt AUROC values were 0.923, 0.808, and 0.776 for XGBoost and 0.918, 0.772, and 0.737 for CareNL-LLM at 1 month, 1 year, and 5 years, respectively. Complete confidence intervals, calibration diagnostics, DCA summaries, coefficients, and locked-threshold results are in `results/tables/`. The manuscript calibration and decision-curve panels are in `results/figures/`.

These results describe one internal study cohort. They do not demonstrate external validity, and the published coefficients and thresholds are not clinical deployment settings.
