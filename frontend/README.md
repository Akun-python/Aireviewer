# Frontend Guide

## Product Role

- React is the primary public-facing workflow UI.
- Streamlit remains the control console and compatibility entry.
- All task pages connect to the same backend run center.

## Start Backend

```powershell
python api_server.py
```

Default API address: `http://127.0.0.1:8011`

## Start React

```powershell
cd frontend
npm install
npm run dev
```

Default Vite dev address: `http://127.0.0.1:5174`

## Preview Production Build

```powershell
cd frontend
npm run build
npm run preview
```

Default preview address: `http://127.0.0.1:4174`

## Run Frontend Tests

```powershell
cd frontend
npm run test
```

## Main Routes

- `/`
- `/reports`
- `/report-complete`
- `/report-integrate`
- `/runs`
- `/presets`
- `/settings`

## Keep Streamlit Available

```powershell
streamlit run streamlit_app.py
```

Default Streamlit address: `http://127.0.0.1:8501`
