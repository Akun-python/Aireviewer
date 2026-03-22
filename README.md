<p align="center">
  <img src="resource/title-banner.svg" alt="Word Revision Agent banner" width="100%" />
</p>

<h1 align="center">Word Revision Agent</h1>

<p align="center">
  面向 <strong>Word 校稿</strong>、<strong>报告生成</strong> 与 <strong>格式规范化</strong> 的多代理工作流
</p>

<p align="center">
  Streamlit UI · LangGraph / Deep Agents · pywin32 · python-docx
</p>

<table>
  <tr>
    <td align="center" width="20%">
      <img src="resource/icon-agent.svg" alt="Agent workflow" width="72" />
      <br />
      <strong>Agent Review</strong>
      <br />
      分段审阅、上下文记忆、断点续跑
    </td>
    <td align="center" width="20%">
      <img src="resource/icon-word.svg" alt="Word revision" width="72" />
      <br />
      <strong>Word Revision</strong>
      <br />
      批注清理、批量修订、DOCX 工作流
    </td>
    <td align="center" width="20%">
      <img src="resource/icon-report.svg" alt="Report generation" width="72" />
      <br />
      <strong>Report Generation</strong>
      <br />
      课题报告生成、已有报告完善、多章节整合
    </td>
    <td align="center" width="20%">
      <img src="resource/icon-format.svg" alt="Format profiles" width="72" />
      <br />
      <strong>Format Profiles</strong>
      <br />
      论文标准、A4 规范、正大杯格式、自动题注
    </td>
    <td align="center" width="20%">
      <img src="resource/icon-ui.svg" alt="Streamlit interface" width="72" />
      <br />
      <strong>Interactive UI</strong>
      <br />
      可视化参数配置、日志预览与结果导出
    </td>
  </tr>
</table>

This project implements an agent-driven Word revision workflow using Deep Agents.

## Structure

- app/: runtime code
- app/agents/: agent setup and prompts
- app/tools/: Word parsing and revision tools
- app/workflows/: orchestration pipeline
- docs/: project notes, references, and non-runtime prompt materials moved out of the repo root
- archive/legacy_text_analysis/: archived early text-counting and analysis experiments moved out of the repo root

## Quick start

- Install dependencies:
  - `pip install -r requirements.txt`
- Configure environment variables (recommended via `.env` in project root):
  - `OPENAI_API_KEY` (or `API_KEY`) **required** for model calls
  - `API_BASE_URL` / `OPENAI_BASE_URL` (optional; OpenAI-compatible base URL, defaults to DeepSeek)
  - `TAVILY_API_KEY` (optional; required only when enabling web search/report generation)
- Run:
  - `python -m app.main --input input.docx --output revised.docx --intent "..." --expert "..."`
  - Convenience wrapper: `python main.py --input input.docx --output revised.docx --intent "..."`
  - Optional: clear existing Word comments first:
    - `python -m app.main --strip-existing-comments --input input.docx --output revised.docx --intent "..." --expert "..."`

## GitHub Prep

- Generated folders such as `tmp/`, `workspace/`, caches, editor state, and `.env` are excluded by `.gitignore`.
- The root `main.py` is now a thin wrapper around `app.main`, so CLI behavior stays aligned in one place.

## Notes

- The primary revision engine uses `win32com` when available.
- `python-docx` is a fallback for simple insert/replace simulation.
- Streamlit UI provides a toggle "开始审阅前删除原文批注" to control whether existing comments are removed before processing.
- Chunked review now includes cross-chunk context by default; tune via `REVIEW_CHUNK_CONTEXT` (default `2`, `0` to disable).
- Persistent context memory (recommended for long documents to keep terminology/style consistent across chunks/reruns):
  - `REVIEW_MEMORY_SCOPE=off|run|session|document` (default `document`)
  - Memory is persisted under `workspace/agent_state/checkpoints.sqlite` (when `AGENT_PERSIST_SESSIONS=true`).
  - When memory is enabled, the backend forces sequential planning by default (disables parallel chunk planning) for consistency; set `REVIEW_MEMORY_ALLOW_PARALLEL=true` to keep parallel.
  - Planning thread mode (when memory is enabled): `REVIEW_PLAN_THREAD_MODE=per_chunk|shared` (default `per_chunk`). Use `shared` only for short documents; long documents may exceed the model context window.
  - Document-scope memory now prefers a stable embedded document id (custom property) when available, so memory can survive iterative revisions of the same document:
    - `REVIEW_MEMORY_EMBED_DOC_ID=true|false` (default `true`)
    - `REVIEW_MEMORY_DOC_ID_PROP=ReviewerDocId` (optional override)
  - Document-scope fingerprint tuning:
    - `REVIEW_MEMORY_FINGERPRINT_MODE=text|bytes` (default `text`, more stable across Word re-saves)
    - `REVIEW_MEMORY_FINGERPRINT_TEXT_CHARS` (default `200000`)
    - `REVIEW_MEMORY_FINGERPRINT_BYTES` (bytes-mode only; default full file)
- Prompt context optimization:
  - `REVIEW_INLINE_CONTEXT=none|boundary|all` (default `boundary`) to reduce duplicated neighbor context lines and fit more useful text into the model context window.
  - `REVIEW_CONTEXT_MAX_CHARS=0|N` (default `1200`) to truncate only CTX_* reference paragraphs (not target paragraphs) to save context window. Set `0` to disable truncation.

## Real-time Save + Resume

- Revision apply supports periodic autosave and resume after interruption:
  - During Win32 apply, output doc is created early and autosaved every N processed instructions.
  - Apply progress is persisted under `workspace/agent_state/revision_resume/*.apply.json`.
  - If a run is interrupted, rerun with the same resume key to continue from checkpoint.
- Environment variables:
  - `REVIEW_RESUME_ENABLED=true|false` (default `true`)
  - `REVIEW_RESUME_DIR=<path>` (default `workspace/agent_state/revision_resume`)
  - `REVIEW_RESUME_KEY=<stable-key>` (pipeline auto-generates a stable key in Streamlit/CLI flow)
  - `REVIEW_APPLY_CHECKPOINT_EVERY=<N>` (default `1`, checkpoint write interval by instruction count)
  - `REVIEW_AUTOSAVE_EVERY=<N>` (default `10`, Word autosave interval by instruction count)
  - `REVIEW_AUTOSAVE_INTERVAL_SECONDS=<seconds>` (default `1.0`, autosave time throttle)
  - `REVIEW_PROTECTED_FORCE_COMMENT_ONLY=true|false` (default `false`; when `true`, protected docs use comment-only fallback)
  - `REVIEW_INSERT_AFTER_COMMENT_FALLBACK=true|false` (default `true`; when insert_after fails, auto-fallback to comment instead of hard failure)

## Streamlit Log Throttling

- To reduce websocket noise when the browser disconnects during long runs, Streamlit live-log rendering is throttled and tailed.
- Environment variables:
  - `STREAMLIT_LOG_UPDATE_INTERVAL_MS=<N>` (default `400`; minimum UI refresh interval)
  - `STREAMLIT_LOG_TAIL_LINES=<N>` (default `300`; only keep/render latest lines in previews)
  - `STREAMLIT_LOG_BUFFER_LINES=<N>` (default `3000`; in-memory rolling buffer for live log box)

## Table Element Extraction

- Streamlit “智能校稿”侧边栏支持“提取表格元素(JSON)”：
  - 输出 `*.tables.json`（表格单元格文本、合并信息、表格内图片路径等）
  - 可选“表格图片理解(APIYI)”：导出表格图片并调用图片理解智能体解析（需 `APIYI_API_KEY`）
  - 默认优先使用 Win32 Word（pywin32，支持 .docx/.doc）；未安装 Word 时自动使用 python-docx 兜底（仅 docx-like，对浮动图形/图表支持有限）
- 相关环境变量：
  - `EXTRACT_TABLE_ELEMENTS=true|false`
  - `TABLE_IMAGE_UNDERSTANDING=true|false`
  - `TABLE_IMAGE_PROMPT="..."`（默认“描述分析这张图”）
  - `APIYI_API_KEY=...`（图片理解接口密钥）

## DOCX Image Extraction

- Streamlit “智能校稿”侧边栏支持“提取文档图片(全局)”：
  - 输出 `*.images.json` 与 `*_images/`（从 docx 的 `word/media/` 导出所有嵌入图片，包含正文/页眉页脚/表格等）
  - 另外会尝试使用 Win32 Word 以 HTML 方式导出“渲染后的图像”（图表/形状/SmartArt 等），补齐不在 `word/media/` 的内容；Win32 不可用时自动跳过
- 相关环境变量：
  - `EXTRACT_DOCX_IMAGES=true|false`

## Topic Report Generator

- Streamlit sidebar supports a “课题报告生成” mode.
- Enter a topic and (optionally) customize the framework to generate a ~10k Chinese report.
- Requires `TAVILY_API_KEY` for web search; outputs `.docx`, `.txt`, and a sources JSON file.
- “完善已有报告” supports filling missing sections based on the existing Word目录（requires Win32 Word via pywin32).
- Word 输出引擎默认优先使用 Win32 Word（pywin32），可通过环境变量 `REPORT_DOCX_ENGINE=python-docx` 强制使用 python-docx。
- “论文标准格式”排版（Win32 Word）：统一页边距、字体字号、段前后与 1.5 倍行距，并自动生成/更新目录与多级编号。
- 可通过环境变量 `REPORT_FORMAT_PROFILE=none` 关闭排版；`REPORT_TOC_POSITION=before_outline|after_title|none` 控制目录位置。
- “报告整合（多章节 Word 合并）”：读取各章节 Word，自动生成《引言》（研究背景/研究内容/研究方法/研究意义）与章节过渡段，统一排版并自动插入图/表题注编号（需要 Win32 Word via pywin32）。

## Screenshots / 界面与结果预览

### Smart Review Workspace / 智能校稿界面

![Smart Review Workspace / 智能校稿界面](resource/智能校稿界面.png)

中文：该界面展示了 Streamlit 版“智能校稿”工作台。左侧用于配置功能模式、审阅引擎、排版风格、上下文与记忆参数；中间区域用于上传 Word 文档、输入审阅角色与修改要求；右侧用于执行任务、查看最近一次结果、下载修订文档与修订摘要。

English: This screenshot shows the Streamlit-based smart review workspace. The left panel configures mode, engine, formatting, context, and memory settings; the center panel is used to upload Word files and define review instructions; the right panel is used to start runs, inspect the latest result, and download revised documents and revision summaries.

### Revision Output Preview / 修订结果预览

![Revision Output Preview / 修订结果预览](resource/修订结果.png)

中文：修订完成后，系统会在 Word 文档中保留原文并以批注形式标出问题与修改建议，便于人工复核、逐条确认和二次编辑。该结果形式适合论文、报告、综述等正式文档的精修场景。

English: After revision, the system preserves the original text in Word and surfaces issues and edit suggestions as comments. This makes manual review, selective acceptance, and follow-up editing straightforward, especially for formal documents such as papers, reports, and literature reviews.

## Resource Assets / 资源文件

- `resource/智能校稿界面.png`: 智能校稿主界面截图 / Main screenshot of the smart review workspace
- `resource/修订结果.png`: Word 修订结果截图 / Screenshot of the Word revision result
