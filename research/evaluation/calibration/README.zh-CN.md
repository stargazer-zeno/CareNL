# 概率校准结果

[English](README.md)

本目录公开与论文金标准一致的 XGBoost 和 CareNL-LLM 概率校准汇总结果。Platt scaling 为主要校准方法，isotonic regression 为敏感性分析。公开内容仅包括汇总表、论文图和 Platt 参数，不包含 EHR、患者级预测、患者分组明细、源清单、模型序列化文件或临床部署配置。

固定划分基于 1,181 名测试集患者：先按字典序排列患者 ID，再使用 NumPy `default_rng(seed=42)` 仅置乱一次，前 392 名用于校准，其余 789 名用于评估。由于随访可评估性不同，各期限的实际患者数、锚点数和阳性数见 `results/tables/calibration_split.csv`。两类模型和三个期限共用同一患者划分。

## 公开内容

- `parameters/platt_parameters.json`：按现有兼容结构保存的 XGBoost Platt 参数。
- `results/tables/platt_parameters.csv`：XGBoost 与 CareNL-LLM 的完整 Platt 参数及校准样本数。
- `results/tables/overall.csv`：AUROC、AUPRC 和 Brier score。
- `results/tables/calibration.csv`：校准诊断指标。
- `results/tables/paired.csv`：原始概率与 Platt 校准概率的配对 Brier 差值。
- `results/tables/dca_summary.csv`：决策曲线汇总。
- `results/tables/locked_operating_points.csv`：锁定阈值的诊断指标和净获益。
- `results/figures/`：论文中的校准曲线和决策曲线。

`run_calibration_analysis.py`、`verify_calibration_outputs.py` 和 `calibration_common.py` 为需要私有授权输入的分析工具，本次仅同步数据，未修改这些脚本。脚本不包含私有的固定患者分组；本目录中的论文对齐 CSV 和图为公开汇总结果的权威版本。

该研究是患者不重叠的内部评估，并非外部验证；模型未重新训练。公开参数和锁定的研究阈值依赖固定模型、源预测、结局定义和研究队列，不会被 `apps/risk-prediction-system` 加载，也不构成临床部署建议。任何前瞻性使用均需独立验证、治理审批和本地重新校准。
