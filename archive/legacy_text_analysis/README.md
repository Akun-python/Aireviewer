# Legacy Text Analysis Archive

This folder stores early one-off text counting and analysis scripts that were previously left in the repo root.

Why these files were archived:

- They are not referenced by the current application entrypoints (`main.py`, `streamlit_app.py`, `app/`).
- Many of them use hard-coded sample text or absolute root paths such as `/text_to_count.txt` and `/final_count.py`.
- Several wrappers only call each other and do not connect to the current Word revision workflow.
- Some files show encoding issues and appear to be historical experiments rather than maintained utilities.

Current active entrypoints remain:

- `python main.py ...`
- `streamlit run streamlit_app.py`

Archive layout:

- `scripts/`: legacy Python and shell wrappers
- `data/`: sample text files and outputs used by those scripts
