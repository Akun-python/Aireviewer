# React + Streamlit Dual Frontend Design

## Goal

Build a smoother, workflow-oriented React frontend without losing the current Streamlit frontend.

The key principle is:

1. Keep the Python document-processing workflows as the single source of truth.
2. Extract a reusable backend service layer from `streamlit_app.py`.
3. Add a small HTTP API layer for React.
4. Keep Streamlit as a thin operations console that calls the same service layer.

This avoids duplicate business logic and keeps the migration risk under control.

## Current State

The current app is already close to a reusable backend shape:

- `streamlit_app.py` contains most UI state, interaction flow, and file handling.
- Core review workflow is already isolated in [app/workflows/pipeline.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/app/workflows/pipeline.py).
- Report generation is already isolated in [app/workflows/report.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/app/workflows/report.py).
- Report integration is already isolated in [app/workflows/report_integrate.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/app/workflows/report_integrate.py).
- Runtime configuration is already centralized in [app/settings.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/app/settings.py).

The real issue is not backend capability. The issue is that UI orchestration, environment mutation, run state, and result rendering are mixed inside [streamlit_app.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/streamlit_app.py).

## Recommendation

Yes, it can be changed to a React frontend.

The recommended architecture is:

1. React handles the product-style workflow UI.
2. FastAPI handles upload, job execution, progress, and downloads.
3. Existing Python workflow modules continue to do document parsing, revision, report generation, and Word output.
4. Streamlit remains available as an internal console or lightweight fallback frontend.

This is a dual-frontend architecture, not a rewrite.

## Target Architecture

### Layers

`Workflow Core`

- `app/workflows/pipeline.py`
- `app/workflows/report.py`
- `app/workflows/report_integrate.py`
- `app/tools/*`
- `app/formatting/*`

`Service Layer`

- New module group: `app/services/*`
- Responsibility:
  - validate requests
  - map UI options into workflow parameters
  - manage workspace paths
  - create run records
  - capture logs and progress events
  - standardize output payloads

`API Layer`

- New module group: `app/api/*`
- Recommended framework: FastAPI
- Responsibility:
  - expose REST endpoints
  - expose SSE or WebSocket progress stream
  - serve file downloads
  - provide health and capability inspection

`Frontends`

- `frontend/` React app for product UI
- existing [streamlit_app.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/streamlit_app.py) simplified into a thin client over `app/services/*`

## Why This Direction

If React talks directly to Python scripts or if Streamlit and React each keep their own business logic, the project will drift quickly.

A shared service layer gives you:

- one workflow implementation
- one validation model
- one run metadata format
- one download/result contract
- one place for logging and resumability

That is the only maintainable way to support both React and Streamlit.

## UX Design Direction

The current Streamlit page is functional but dense. React should change the interaction model from "all controls on one screen" to "guided workflow".

### Primary Navigation

Top-level products:

1. Smart Review
2. Report Generation
3. Report Completion
4. Multi-chapter Integration
5. Run History
6. Settings

### Smart Review Flow

Use a 4-step workflow instead of a large one-page form.

Step 1: Upload

- drag-and-drop Word file
- show file name, size, type, upload status
- detect available engine capability
- show quick warnings before user continues

Step 2: Review Intent

- choose review role
- choose preset prompt
- fill or append prompt text
- enter review goal
- toggle focus review
- show default constraints as read-only checklist

Step 3: Strategy

- select engine
- select formatting profile
- choose memory mode
- choose context strategy
- choose expansion level
- choose web search
- choose table/image extraction
- advanced options collapsed by default

Step 4: Run and Inspect

- live progress timeline
- log panel
- generated artifact cards
- summary JSON preview
- download buttons
- open result folder action

### Report Flow

React should use the same structure:

1. Topic and framework
2. Search and generation strategy
3. Formatting and output
4. Run monitor and exports

### Run History

The current Streamlit session/history model can become a proper run center:

- recent runs list
- status filter
- reopen run detail
- re-run with same parameters
- compare run settings
- download previous artifacts

## Suggested React UI Structure

Recommended stack:

- React
- Vite
- TypeScript
- TanStack Query
- React Router
- Zustand or Redux Toolkit for transient workflow state
- Ant Design, Mantine, or shadcn/ui

Recommended page structure:

- `frontend/src/pages/SmartReviewPage.tsx`
- `frontend/src/pages/ReportPage.tsx`
- `frontend/src/pages/ReportCompletePage.tsx`
- `frontend/src/pages/ReportIntegratePage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`

Recommended shared UI components:

- `FileDropzone`
- `WorkflowStepper`
- `IntentEditor`
- `PresetPromptPicker`
- `EngineSelector`
- `MemorySettingsPanel`
- `AdvancedOptionsDrawer`
- `RunProgressPanel`
- `ArtifactList`
- `ResultSummaryViewer`
- `CapabilityBadgeGroup`

## Suggested Backend Refactor

### New service modules

Add:

- `app/services/review_service.py`
- `app/services/report_service.py`
- `app/services/run_store.py`
- `app/services/capability_service.py`
- `app/services/log_stream.py`

Responsibilities:

`review_service.py`

- accept a typed review request
- save upload to workspace
- build output paths
- call `run_revision`
- build normalized result payload

`report_service.py`

- wrap `generate_report`
- wrap `complete_report_docx`
- wrap `integrate_report_chapters`
- standardize report outputs

`run_store.py`

- persist run metadata
- persist status
- map run id to artifacts
- support run history for both frontends

`capability_service.py`

- detect Win32 availability
- detect `python-docx`
- detect API keys
- return capabilities to both frontends

`log_stream.py`

- capture workflow logs
- expose append/read/subscribe API
- support SSE/WebSocket streaming

### Request models

Add typed request/response models, ideally with Pydantic in the API layer:

- `ReviewRequest`
- `ReviewResult`
- `ReportRequest`
- `ReportResult`
- `RunStatus`
- `CapabilityResponse`

That will remove the current pattern where UI code writes many environment variables inline before calling workflows.

## Recommended API Design

### Core endpoints

`GET /api/health`

- returns service health

`GET /api/capabilities`

- returns engine and environment capabilities

`POST /api/review/upload`

- upload Word file and return temp file token

`POST /api/review/runs`

- create a review run

`GET /api/review/runs/{run_id}`

- return run status and metadata

`GET /api/review/runs/{run_id}/events`

- SSE progress stream

`GET /api/review/runs/{run_id}/artifacts`

- return downloadable artifacts

`POST /api/report/runs`

- create report generation run

`POST /api/report-complete/runs`

- create report completion run

`POST /api/report-integrate/runs`

- create multi-chapter integration run

`GET /api/runs`

- list all runs

`GET /api/files/{artifact_id}`

- download file

### Progress transport

Preferred choice: SSE first, WebSocket second.

Reason:

- easier than WebSocket for one-way progress updates
- good fit for job logs and status events
- simpler for React and Python

Event types:

- `run.created`
- `run.started`
- `run.progress`
- `run.log`
- `run.artifact.ready`
- `run.completed`
- `run.failed`

## Streamlit Compatibility Plan

Do not delete Streamlit.

Keep it in two possible roles:

### Option A: Full fallback frontend

Streamlit remains a complete frontend for internal use, low-code operations, and quick debugging.

### Option B: Operations console

Streamlit becomes an admin console focused on:

- raw logs
- artifact inspection
- environment diagnostics
- prompt testing
- recovery and reruns

Option B is the better long-term direction, but Option A is the faster migration path.

## Directory Proposal

```text
reviewer/
  app/
    api/
      main.py
      routes_review.py
      routes_report.py
      routes_runs.py
      models.py
    services/
      review_service.py
      report_service.py
      run_store.py
      capability_service.py
      log_stream.py
    workflows/
    tools/
    formatting/
  frontend/
    src/
      pages/
      components/
      hooks/
      api/
      store/
      types/
  streamlit_app.py
```

## Migration Strategy

### Phase 1: Backend extraction

Goal:

- no product change
- only move logic out of `streamlit_app.py`

Tasks:

- extract review run creation into service layer
- extract report actions into service layer
- create unified run result schema
- make Streamlit call services instead of directly mutating workflow env everywhere

### Phase 2: API layer

Goal:

- expose stable HTTP contracts

Tasks:

- add FastAPI app
- add run creation endpoints
- add capability endpoint
- add artifact downloads
- add SSE log streaming

### Phase 3: React frontend

Goal:

- ship workflow-oriented product UI

Tasks:

- build guided stepper flow
- integrate upload and run APIs
- add run history
- add result artifact center

### Phase 4: Streamlit simplification

Goal:

- reduce duplicated UI complexity

Tasks:

- remove duplicated path-building and run-state logic
- keep only thin orchestration and admin-oriented views

## Key Technical Adjustments Needed

### 1. Replace environment-heavy UI orchestration

Today, many options are passed by setting process environment variables inside [streamlit_app.py](C:/Users/24260/Desktop/Auto数据分析项目/modules/reviewer/streamlit_app.py).

That is acceptable for one local frontend, but weak for a shared backend serving React and Streamlit.

Recommended change:

- introduce explicit request objects
- convert request objects into workflow configuration inside service functions
- keep environment variables only for deployment defaults, not per-request state

### 2. Standardize run records

Each run should have:

- `run_id`
- `mode`
- `status`
- `created_at`
- `started_at`
- `finished_at`
- `input_files`
- `params`
- `artifacts`
- `summary`
- `error`

### 3. Make logs first-class

Current logging is file-based and Streamlit-tail oriented.

That should evolve into:

- append to file for durability
- append to in-memory event stream for real-time UI
- expose same logs to React and Streamlit

### 4. Separate user-friendly labels from backend enums

Frontend should use localized labels, but backend should use stable values such as:

- `revision_engine: auto | win32com | python-docx`
- `memory_scope: off | run | session | document`
- `format_profile: none | thesis_standard | zhengda_cup | a4_strict`

## UX Improvements React Can Deliver

React is worth doing if the goal is not just "prettier UI" but better flow and recoverability.

It can improve:

- guided steps instead of a long settings wall
- better progress visualization
- resumable runs with visible status
- cleaner artifact center
- richer run history
- better mobile and wide-screen layout control
- clearer advanced-vs-basic separation

## Risks

### Risk 1: Duplicate business logic

If React gets its own logic and Streamlit keeps the old logic, bugs will diverge.

Mitigation:

- move logic into `app/services/*`

### Risk 2: Long-running request handling

Review and report generation are not quick CRUD requests.

Mitigation:

- use background job model
- stream progress through SSE
- store artifacts by run id

### Risk 3: Windows and Word dependency

Win32 Word is a desktop dependency and affects deployment model.

Mitigation:

- keep backend on Windows host
- expose capabilities clearly in UI
- support `python-docx` fallback in both frontends

### Risk 4: Overbuilding too early

A full microservice split is unnecessary at this stage.

Mitigation:

- keep one Python backend process
- add React only as a new frontend
- split further only when concurrency demands it

## Recommended First Implementation Slice

The best first slice is not the whole React product. It is this:

1. Extract `review_service` from Streamlit logic.
2. Add `GET /api/capabilities`.
3. Add `POST /api/review/runs`.
4. Add `GET /api/review/runs/{run_id}`.
5. Add `GET /api/review/runs/{run_id}/events`.
6. Build one React page for Smart Review only.
7. Keep report features in Streamlit until the review flow is stable.

This gives the biggest UX gain with the lowest migration risk.

## Final Decision

Yes, React is appropriate here.

But the correct implementation is:

- not "replace Streamlit with React"
- not "maintain two separate frontends with separate logic"
- instead "shared Python service layer + FastAPI + React + Streamlit fallback"

That is the cleanest way to improve interaction flow while preserving the current working system.
