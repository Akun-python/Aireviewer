# Frontend Run Guide

## Start the API

```powershell
C:\Users\24260\.conda\envs\data_analysis_py311\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8011 --reload
```

## Start the React frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5174` and proxies `/api` requests to `http://127.0.0.1:8011`.

## Keep Streamlit available

```powershell
streamlit run streamlit_app.py
```

The current first implementation slice focuses on the React smart-review flow. Report-related flows remain available in Streamlit.
