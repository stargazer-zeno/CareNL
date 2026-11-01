# CareNL 预测系统

[English](README.md)

该系统面向小儿肝移植术后随访死亡风险科研评估。用户上传标准化纵向记录后，系统输出未来 1 个月、1 年和 5 年的 CareNL 风险概率。

> 仅限科研与软件演示，不用于诊断、治疗、预后沟通或个体临床决策。

## 系统结构

React/nginx → FastAPI → 输入适配器 → OpenAI-compatible LLM API。

CareNL 仅使用大模型输出 1 个月、1 年、5 年死亡风险、模式分析和总结，不再加载或调用 XGBoost。历史 ML 源码和模型文件保留在仓库，运行镜像不包含模型和 ML 专用依赖。显式 `null` 和部分结果保留，不补全概率。

## Docker 部署

复制 `.env.example` 为 `.env`，配置 `LLM_BASE_URL`（包含 `/v1`）和与远程部署一致的 `LLM_MODEL_NAME`，然后运行 `docker compose up -d --build`。已有 `.env` 时保留原配置。

`LLM_BASE_URL` 留空时应用仍可启动，但预测不可用。`/health` 只检查应用存活，`/api/health` 同时报告远程连接和模型是否匹配。

默认页面端口为 8080，API 端口为 8000；可通过 `FRONTEND_PORT` 和 `BACKEND_PORT` 覆盖。本机沿用页面 http://localhost:18080 和 API http://localhost:18000，文档位于 `/docs`。

### 可选本地 vLLM

本地模式要求 Linux Docker、NVIDIA 驱动、NVIDIA Container Toolkit，以及满足上下文长度要求的 GPU 显存。

```bash
# Hugging Face 模型需要鉴权时才设置 HF_TOKEN。
export HF_TOKEN="replace-with-hugging-face-token"
docker compose -f compose.yaml -f compose.vllm.yaml --profile llm up -d --build
```

vLLM API 映射到 <http://localhost:8001/v1>。可通过 `VLLM_MAX_MODEL_LEN` 和 `VLLM_TENSOR_PARALLEL_SIZE` 调整资源配置。

## 输入与样例

支持 JSON、JSONL、CSV 和 XLSX。`frontend/public/samples/` 中仅保留两个明确标注的合成样例，不包含真实身份、结局标签或精确临床日期。

上传记录和结果仅保存在本机 Docker volume。若部署到共享网络，必须另行配置身份认证、TLS、访问控制、留存策略并通过机构隐私审查。

## 测试

```bash
cd backend
python -m pytest

cd ../frontend
npm ci
npm test
npm run build
```

## 接口迁移与历史任务

- `/api/predict`、`/api/batch_predict` 和异步任务接口保持原路径。预测对象为 `{id, llm}`，移除 `ml` 字段。
- `/predict` 和 `/batch_predict` 停用并返回 HTTP 410，调用方应迁移至对应 `/api/` 路径。
- JSON 仅含 LLM 结果，CSV 仅保留 `id` 和 `llm_` 列。历史任务原文件不修改，读取及下载时仅投影已有 LLM 结果。
- `completed` 为已处理记录数，`failed` 统计错误、禁用或缺失结果；`partial` 为部分成功，不计入失败。任务完成不代表所有记录预测成功。
- 应用测试不需要本地模型。历史模型测试仅在安装可选 XGBoost/scikit-learn 依赖后运行。

## 英文展示样例与输出

两个 `frontend/public/samples/` 样例已使用英文字段、取值及临床事件描述；数值和时序顺序保持不变。顶层字段为 `basic_information`、`followup_series`、`laboratory_series`、`medication_series` 和可选的 `clinical_events`。仍兼容旧中文输入字段，但同一部分不能同时提交中英文别名。

预测及二次总结提示词均要求英文。趋势标签使用 `worsening`、`abnormal`、`fluctuating`、`sudden_abnormality`、`improving`、`normal`。输出标签及概率键保持不变。

若模型仍生成中文，返回 `output_language_error` 英文错误提示，不展示或导出该文本作为有效预测。历史中文结果读取时也进行检查，原文件不变。模型是否能稳定生成英文，需要在远程服务部署后实测。
