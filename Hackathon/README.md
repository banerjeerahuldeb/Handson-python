
# IntelliKnow Hub — Streamlit Demo

Lightweight prototype to capture **screenshots** for the IntelliKnow Hub hackathon submission.

## Features
- Role-based (simulated) security trimming
- Tower & Source filters
- Natural-language search (TF-IDF + cosine similarity)
- Result cards with tags, relevance, and links
- Conversational assistant that **always cites** the source docs
- Demo analytics with query log + CSV export

## How to Run
```bash
# 1) Create a virtualenv (recommended)
python -m venv .venv
# Windows:
# .venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# 2) Install deps
pip install streamlit scikit-learn pandas

# 3) Run the app
streamlit run app.py
```
Open the URL shown in your terminal (typically `http://localhost:8501`).

## Files
- `app.py` — Streamlit application
- `documents.json` — Dummy knowledge documents with allowed_roles
