# Calibration protocol

## Objective

Assess post-hoc probability calibration for the fixed XGBoost and CareNL-LLM risk models at 1-month, 1-year, and 5-year horizons without retraining either model.

## Fixed design

1. Sort the 1,181 test-set patient IDs lexicographically and permute them once with NumPy `default_rng(seed=42)`.
2. Assign the first 392 patients to calibration and the remaining 789 patients to evaluation. Use the same patient assignment for both models and all horizons.
3. Apply horizon-specific follow-up eligibility. The calibration/evaluation counts are 392/789 patients at 1 month, 359/710 at 1 year, and 231/452 at 5 years; the corresponding anchor and positive counts are recorded in `results/tables/calibration_split.csv`.
4. Fit Platt scaling on the logit of clipped raw probabilities in the calibration subset. Fit isotonic regression as a sensitivity analysis.
5. Apply the fitted mappings unchanged to the evaluation subset.
6. Report AUROC, AUPRC, Brier score, calibration diagnostics, decision-curve summaries, paired Brier-score changes, and locked-threshold operating characteristics.
7. Use patient-level cluster bootstrap resampling with seed `20260922`, 2,000 requested replicates, and at least 1,800 valid replicates for conditional estimates. The released paired Brier results contain 2,000 valid replicates.

## Interpretation rules

- Platt scaling is monotonic, so AUROC and AUPRC are unchanged apart from numerical precision.
- Brier score and calibration diagnostics assess probability quality; they do not establish clinical utility by themselves.
- Decision curves and locked thresholds are descriptive study outputs, not deployment recommendations.
- The patient-disjoint evaluation is internal. External validation and local recalibration remain necessary before clinical use.
