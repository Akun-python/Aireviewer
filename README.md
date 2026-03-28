<p align="center">
  <img src="resource/title-banner.svg" alt="Academic Writing Assistant banner" width="100%" />
</p>

# 学术文稿助手 / Academic Writing Assistant

面向中文社科论文、课题申报书、活页、文献综述的本地优先开源项目。它将 `智能校稿`、`学术诊断`、`课题报告生成`、`报告完善`、`多章整合` 收敛到同一套服务层、API 和运行中心之下。

Academic Writing Assistant is a local-first open-source project for Chinese academic writing workflows. It unifies smart review, structured diagnostics, report generation, report completion, and chapter integration under one shared service layer and one run center.

## 项目定位 / Positioning

- 中文：项目当前聚焦 `中文社科 / 课题申报 / 文献综述 / 学术论文润色与一致性核查`，不是泛化到合同、制度或企业办公文档的通用 Word 工具。
- English: The current scope is `Chinese social science papers, fund applications, literature reviews, and academic review workflows`, not a generic Word processor for all enterprise documents.

## 界面预览 / Screenshots

### 智能校稿界面 / Smart Review Workspace

![智能校稿界面 / Smart Review Workspace](resource/智能校稿界面.png)

中文：React 作为主入口提供流程化工作台；Streamlit 继续保留完整控制台入口，便于调试、排查和参数细调。

English: React is the primary workflow UI, while Streamlit remains available as the full control console for debugging and deep parameter tuning.

### 修订结果 / Revision Result

![修订结果 / Revision Result](resource/修订结果.png)

中文：修订结果保留 Word 可交付文档形态，同时输出修订摘要、运行日志与学术诊断 JSON，方便人工复核。

English: The result keeps a deliverable Word document and also emits revision summary, run logs, and diagnostics JSON for manual verification.

### 课题报告生成 / Report Workflow

![课题报告生成 / Report Workflow](resource/report-workflow.png)

English: Topic report generation page with framework editing, generation parameters, and a side-by-side result area.

### 报告完善 / Report Completion

![报告完善 / Report Completion](resource/report-complete-workflow.png)

English: Existing report completion workflow with document upload, completion switches, and run feedback panels.

### 多章整合 / Chapter Integration

![多章整合 / Chapter Integration](resource/report-integrate-workflow.png)

English: Multi-chapter integration page for combining Word sections into one structured report package.

### 运行中心 / Run Center

![运行中心 / Run Center](resource/run-center.png)

English: Centralized run list for review and report workflows, including recent tasks and status tracking.

### 预设规则 / Preset Library

![预设规则 / Preset Library](resource/preset-library.png)

English: Shared preset cards exposed to both React and Streamlit, showing roles, diagnostics dimensions, and default constraints.

### 设置 / Settings & Ops

![设置 / Settings & Ops](resource/settings-ops.png)

English: Environment capability overview covering interfaces, API endpoint, and local runtime readiness.

## 当前可用入口 / Current Interfaces

| 入口 / Interface | 定位 / Role | 当前能力 / Current Capability |
| --- | --- | --- |
| React | 主产品入口 / Primary product UI | 智能校稿、课题报告、报告完善、多章整合、运行中心、预设规则、设置 |
| Streamlit | 控制台 / Fallback console | 审阅参数最全、日志观察、人工排查、报告类流程兜底 |
| FastAPI | 服务层 / Service layer | Review / diagnostics / presets / report / run-center APIs |
| CLI | 自动化入口 / Automation | 文稿审阅、预设选择、诊断输出、诊断-only 模式 |

## 推荐使用路径 / Recommended Path

- 想直接体验主产品界面：使用 React，默认开发地址是 `http://127.0.0.1:5174`
- 想用完整控制参数或排查问题：使用 Streamlit，默认地址是 `http://127.0.0.1:8501`
- 想做自动化集成：使用 FastAPI 或 CLI

## 核心能力 / Core Capabilities

### 1. 智能校稿 / Smart Review

- 共享学术预设：`general_academic`、`social_science_fund`、`literature_review`
- 共享运行中心：所有任务统一记录到同一个 `RunStore`
- 共享产物中心：修订文档、修订摘要、运行日志、诊断 JSON、表格 JSON、图片 JSON

### 2. 学术诊断 / Academic Diagnostics

诊断结果统一收敛为单个 `*.diagnostics.json`，当前包含：

- 引用 / 参考文献核查
- 章节结构评分
- 术语与缩略语一致性
- 图表与题注核查
- 逻辑与衔接诊断
- 事实 / 数字变更风险

### 3. 报告类流程 / Report Workflows

- 课题报告生成
- 完善已有报告
- 多章节报告整合

## React 路由 / React Routes

- `/`
- `/reports`
- `/report-complete`
- `/report-integrate`
- `/runs`
- `/presets`
- `/settings`

## API 接口 / Public API

### Review

- `POST /api/review/runs`
- `GET /api/review/presets`
- `GET /api/review/runs/{id}/diagnostics`

### Reports

- `POST /api/report/runs`
- `POST /api/report-complete/runs`
- `POST /api/report-integrate/runs`

### Run Center

- `GET /api/runs`
- `GET /api/runs/{id}`
- `GET /api/runs/{id}/events`
- `GET /api/runs/{id}/artifacts/{artifact_name}`

## CLI 用法 / CLI

```powershell
python -m app.main `
  --input .\examples\general_academic\乡村治理研究_示例论文.docx `
  --output .\workspace\demo_review.docx `
  --intent "统一术语、检查章节结构并优化学术表达" `
  --preset general_academic `
  --diagnostics
```

```powershell
python -m app.main `
  --input .\examples\social_science_fund\国社科活页_示例.docx `
  --output .\workspace\fund_review.docx `
  --preset social_science_fund `
  --diagnostics-only
```

支持的重点参数：

- `--preset`
- `--diagnostics`
- `--diagnostics-only`

## 快速开始 / Quick Start

### 中文

1. 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

2. 启动 API

```powershell
python api_server.py
```

默认监听 `http://127.0.0.1:8011`

3. 启动 React

```powershell
cd frontend
npm install
npm run dev
```

默认开发地址 `http://127.0.0.1:5174`

4. 启动 Streamlit 控制台

```powershell
streamlit run streamlit_app.py
```

### English

1. Install Python dependencies

```powershell
pip install -r requirements.txt
```

2. Start the API server

```powershell
python api_server.py
```

Default API address: `http://127.0.0.1:8011`

3. Start the React frontend

```powershell
cd frontend
npm install
npm run dev
```

Default React address: `http://127.0.0.1:5174`

4. Start the Streamlit console

```powershell
streamlit run streamlit_app.py
```

## 运行环境 / Environment

- `OPENAI_API_KEY` or `API_KEY`: 模型调用 / model access
- `TAVILY_API_KEY`: 联网检索 / web search
- `API_BASE_URL` or `OPENAI_BASE_URL`: 兼容 OpenAI 的模型网关 / OpenAI-compatible gateway

## 能力矩阵 / Capability Matrix

完整能力矩阵见：

- [docs/capability_matrix.md](docs/capability_matrix.md)

简要原则：

- Win32 Word 可用时：高保真修订痕迹、目录、排版、章节整合能力完整
- 无 Win32 Word 时：`python-docx` 与 `diagnostics` 仍可运行，但 Word 原生修订痕迹与部分高保真排版能力会降级

## 示例数据 / Example Data

示例文档位于：

- `examples/general_academic`
- `examples/social_science_fund`
- `examples/literature_review`
- `examples/report_integrate`

## 开源说明 / Open Source

- License: [MIT](LICENSE)
- Contribution Guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Frontend Guide: [frontend/README.md](frontend/README.md)

## 目录结构 / Project Structure

- `app/`: runtime code
- `app/api/`: FastAPI routes
- `app/services/`: shared service layer
- `app/workflows/`: review / report workflows
- `frontend/`: React frontend
- `streamlit_app.py`: Streamlit console
- `examples/`: sample documents
- `resource/`: screenshots and visual assets
