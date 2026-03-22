# Contributing

## Scope

This project focuses on local-first academic writing workflows for Chinese social science writing, fund applications, literature reviews, and related report flows.

## Development Setup

```powershell
pip install -r requirements.txt
python api_server.py
```

```powershell
cd frontend
npm install
npm run dev
```

Optional console entry:

```powershell
streamlit run streamlit_app.py
```

## Before Opening a PR

Run the backend checks:

```powershell
python -m compileall app api_server.py tests
python -m pytest
```

Run the frontend build:

```powershell
cd frontend
npm run build
```

## Contribution Guidelines

- Keep React, Streamlit, API, and CLI aligned through the shared service layer.
- Do not add product-only logic directly in one frontend if it should be shared by all entry points.
- Prefer stable enum values for presets and run modes.
- Preserve local-first assumptions. Do not introduce accounts, multi-tenant state, or cloud-only dependencies without discussion.
- Document behavior changes in `README.md` and `docs/capability_matrix.md`.

## Issues and PRs

- Describe the scenario, expected behavior, and observed behavior.
- Include sample input files or reduced repro steps when possible.
- If the change affects Word fidelity, note whether it was verified with Win32 Word or python-docx fallback.
