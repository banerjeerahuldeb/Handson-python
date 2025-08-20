# Build a Gemini-only, persona-aware RAG app project and zip it.
import os, shutil, zipfile, pathlib, textwrap, json

base = "/mnt/data/rag_pdf_excel_gemini_persona"
if os.path.exists(base):
    shutil.rmtree(base)
os.makedirs(base, exist_ok=True)
os.makedirs(f"{base}/app", exist_ok=True)
os.makedirs(f"{base}/uploads", exist_ok=True)
os.makedirs(f"{base}/indexes", exist_ok=True)

requirements = """
streamlit==1.37.1
pandas==2.2.2
numpy==1.26.4
faiss-cpu==1.8.0.post1
sentence-transformers==3.0.1
rank-bm25==0.2.2
pypdf==4.3.1
duckdb==1.0.0
openpyxl==3.1.5
requests==2.32.3
tqdm==4.66.5
Pillow==10.4.0
pdf2image==1.17.0
pytesseract==0.3.13
google-generativeai==0.7.2
"""
open(f"{base}/requirements.txt","w").write(requirements.strip())

readme = """
# PDF + Excel Q&A (Gemini, Personas, OCR) — Local RAG

This app lets you upload **multiple PDFs and Excels**, then ask questions. It uses **Gemini (free API via Google AI Studio)** with a **persona selector** (Plant Operator, Corporate Employee, General Employee) and a stronger **retrieval pipeline** (BM25 + dense + cross‑encoder rerank). It also supports **OCR** for scanned PDFs and an **Excel SQL** mode using DuckDB.

## Requirements
- Python 3.10+
- A **Gemini API key** from Google AI Studio (free tier): https://aistudio.google.com/
- (Optional) **Tesseract OCR** installed and on PATH for scanned PDFs:
  - macOS: `brew install tesseract`
  - Ubuntu: `sudo apt-get install tesseract-ocr`
  - Windows: installer from tesseract-ocr.github.io

## Setup
```bash
pip install -r requirements.txt
# set your key
export GEMINI_API_KEY=YOUR_KEY   # PowerShell: $env:GEMINI_API_KEY="YOUR_KEY"
```

## Run
```bash
streamlit run app/streamlit_app.py
```

## Features
- **Personas** (choose in UI):
  - Plant Operator → safety-first, SOP/checklist style, actionable steps
  - Corporate Employee → KPIs/ROI/risks, concise executive tone
  - General Employee → plain-language guidance
- **RAG**: BM25 + dense vectors (FAISS) + **cross‑encoder** rerank for better context
- **Excel SQL**: Gemini auto-generates **DuckDB SQL** for exact numbers and aggregations
- **OCR**: toggle on for image-only PDFs
- All data stays **local** except the prompts sent to **Gemini** (your choice to use the online API).

## Notes
- Tables are named `{file_stem}__{sheet}` with spaces replaced by `_`.
- If SQL generation fails, correct the SQL and re-run, or switch to RAG mode.
- Consider masking/removing sensitive data before upload.
""".strip()
open(f"{base}/README.md","w").write(readme)

utils_py = """
import re, os, pathlib
from typing import List, Dict, Any
import pandas as pd
import duckdb

_TABLE_NAME_SAFE = re.compile(r"[^0-9a-zA-Z_]+")

def sanitize_table_name(name: str) -> str:
    return _TABLE_NAME_SAFE.sub("_", name)

def excel_to_duckdb(con: duckdb.DuckDBPyConnection, excel_paths: List[str]) -> Dict[str, str]:
    mapping = {}
    for xp in excel_paths:
        try:
            xls = pd.ExcelFile(xp, engine='openpyxl')
            stem = pathlib.Path(xp).stem
            for sheet in xls.sheet_names:
                df = xls.parse(sheet)
                tname = sanitize_table_name(f"{stem}__{sheet}")
                con.register(tname, df)  # temp view
                con.execute(f"CREATE OR REPLACE TABLE {tname} AS SELECT * FROM {tname}")
                mapping[tname] = f"{os.path.basename(xp)} :: {sheet}"
        except Exception as e:
            print(f"Failed to load Excel {xp}: {e}")
    return mapping

def excel_to_text(excel_path: str, max_rows: int = 2000) -> str:
    out_lines = []
    try:
        xls = pd.ExcelFile(excel_path, engine='openpyxl')
        for sheet in xls.sheet_names:
            df = xls.parse(sheet).head(max_rows)
            out_lines.append(f"### File: {os.path.basename(excel_path)} | Sheet: {sheet}")
            out_lines.append("Columns: " + ", ".join(map(str, df.columns)))
            out_lines.append(df.to_csv(index=False))
    except Exception as e:
        out_lines.append(f"[Excel parse error: {e}]")
    return "\\n".join(out_lines)
""".strip()
open(f"{base}/app/utils.py","w").write(utils_py)

ocr_py = """
from typing import Optional
from pdf2image import convert_from_path
import pytesseract

def ocr_pdf(path: str, max_pages: int = 100) -> str:
    \"\"\"OCR first `max_pages` pages from PDF to text.\"\"\"
    texts = []
    pages = convert_from_path(path, dpi=200, first_page=1, last_page=max_pages)
    for img in pages:
        txt = pytesseract.image_to_string(img)
        if txt:
            texts.append(txt)
    return "\\n".join(texts)
""".strip()
open(f"{base}/app/ocr.py","w").write(ocr_py)

retriever_py = """
from typing import List, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

_EMB = None
_RERANK = None

def _emb():
    global _EMB
    if _EMB is None:
        _EMB = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _EMB

def _cross():
    global _RERANK
    if _RERANK is None:
        _RERANK = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _RERANK

def build_dense_index(chunks: List[str]):
    embs = _emb().encode(chunks, normalize_embeddings=True, show_progress_bar=True)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs.astype('float32'))
    return index

def dense_search(index, chunks: List[str], query: str, k: int = 30) -> List[Tuple[int, float]]:
    q = _emb().encode([query], normalize_embeddings=True).astype('float32')
    D, I = index.search(q, k)
    return list(zip(I[0].tolist(), D[0].tolist()))

def bm25_search(chunks: List[str], query: str, k: int = 30) -> List[Tuple[int, float]]:
    tokenized = [c.split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.split())
    order = np.argsort(scores)[::-1][:k]
    return [(int(i), float(scores[int(i)])) for i in order]

def hybrid_search(index, chunks: List[str], query: str, k_dense: int = 30, k_bm25: int = 30, top_k: int = 10):
    dense = dense_search(index, chunks, query, k_dense)
    bm = bm25_search(chunks, query, k_bm25)
    scores = {}
    for i, s in dense:
        scores[i] = max(scores.get(i, 0.0), s)
    for i, s in bm:
        scores[i] = max(scores.get(i, 0.0), s/100.0)
    cand = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max(top_k*4, 20)]
    pairs = [ (query, chunks[i]) for i,_ in cand ]
    rerank_scores = _cross().predict(pairs)
    reranked = sorted(zip([i for i,_ in cand], rerank_scores), key=lambda x: x[1], reverse=True)[:top_k]
    return reranked
""".strip()
open(f"{base}/app/retriever.py","w").write(retriever_py)

gemini_client_py = """
import os
import google.generativeai as genai

def _client(model: str = "gemini-1.5-flash", system_instruction: str = None, temperature: float = 0.2, max_output_tokens: int = 1024):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
    genai.configure(api_key=key)
    config = genai.GenerationConfig(temperature=temperature, max_output_tokens=max_output_tokens)
    if system_instruction:
        return genai.GenerativeModel(model_name=model, system_instruction=system_instruction, generation_config=config)
    return genai.GenerativeModel(model_name=model, generation_config=config)

def gemini_chat_text(system_prompt: str, user_prompt: str, model: str = "gemini-1.5-flash", temperature: float = 0.2, max_output_tokens: int = 1024) -> str:
    m = _client(model=model, system_instruction=system_prompt, temperature=temperature, max_output_tokens=max_output_tokens)
    resp = m.generate_content(user_prompt)
    return getattr(resp, "text", "").strip()

def gemini_text_only(prompt: str, model: str = "gemini-1.5-flash", temperature: float = 0.2, max_output_tokens: int = 1024) -> str:
    m = _client(model=model, temperature=temperature, max_output_tokens=max_output_tokens)
    resp = m.generate_content(prompt)
    return getattr(resp, "text", "").strip()
""".strip()
open(f"{base}/app/gemini_client.py","w").write(gemini_client_py)

streamlit_app_py = """
import os, io, pathlib, shutil, pickle
import streamlit as st
from typing import List, Dict, Any
from pypdf import PdfReader
from app.utils import excel_to_duckdb, excel_to_text
from app.ocr import ocr_pdf
from app.retriever import build_dense_index, hybrid_search
from app.gemini_client import gemini_chat_text, gemini_text_only
import duckdb

INDEX_DIR = "indexes"
UPLOAD_DIR = "uploads"

st.set_page_config(page_title="PDF + Excel Q&A — Gemini + Personas", layout="wide")

st.sidebar.title("📁 Upload & Index")
uploaded_files = st.sidebar.file_uploader(
    "Upload PDFs and/or Excel files (.pdf, .xlsx, .xls)",
    type=["pdf","xlsx","xls"],
    accept_multiple_files=True
)

use_ocr = st.sidebar.checkbox("Use OCR for scanned PDFs (slower)", value=False)

if st.sidebar.button("Clear uploads"):
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    st.sidebar.success("Uploads cleared.")

if st.sidebar.button("(Re)build Index"):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(INDEX_DIR, exist_ok=True)
    saved_paths = []
    if uploaded_files:
        for uf in uploaded_files:
            out_path = os.path.join(UPLOAD_DIR, uf.name)
            with open(out_path, "wb") as f:
                f.write(uf.read())
            saved_paths.append(out_path)
    else:
        saved_paths = [os.path.join(UPLOAD_DIR, p) for p in os.listdir(UPLOAD_DIR)]

    chunks, sources = [], []

    for path in saved_paths:
        p = pathlib.Path(path)
        try:
            if p.suffix.lower() == ".pdf":
                reader = PdfReader(path)
                full_text = []
                for page in reader.pages:
                    txt = page.extract_text() or ""
                    full_text.append(txt)
                text = "\\n".join(full_text)
                if use_ocr and (not text.strip()):
                    text = ocr_pdf(path)
                words = text.split()
                size, overlap = 180, 30
                i = 0
                while i < len(words):
                    ck = " ".join(words[i:i+size])
                    if ck.strip():
                        chunks.append(ck); sources.append(f"{p.name} (PDF)")
                    i += size - overlap
            elif p.suffix.lower() in (".xlsx",".xls"):
                text = excel_to_text(path)
                words = text.split()
                size, overlap = 220, 40
                i = 0
                while i < len(words):
                    ck = " ".join(words[i:i+size])
                    if ck.strip():
                        chunks.append(ck); sources.append(f"{p.name} (Excel)")
                    i += size - overlap
        except Exception as e:
            st.sidebar.error(f"Failed to parse {p.name}: {e}")

    if not chunks:
        st.sidebar.warning("No content to index. Upload files first.")
    else:
        index = build_dense_index(chunks)
        import faiss
        faiss.write_index(index, os.path.join(INDEX_DIR, 'index.faiss'))
        with open(os.path.join(INDEX_DIR,'meta.pkl'),'wb') as f:
            pickle.dump({"chunks":chunks, "sources":sources}, f)
        st.sidebar.success(f"Indexed {len(chunks)} chunks from {len(saved_paths)} files.")

st.title("🔎 PDF + Excel Q&A (Gemini) — Persona‑aware")

persona = st.selectbox("Persona", ["Plant Operator", "Corporate Employee", "General Employee"])

persona_prompts = {
    "Plant Operator": (
        "You are a plant maintenance operator. Be safety‑first, pragmatic, and checklist‑oriented. "
        "Reference SOPs if present. Provide step‑by‑step actions, required permits, spares, and escalation rules. "
        "Prefer concise bullet points; avoid speculation. If unknown, say so."
    ),
    "Corporate Employee": (
        "You are a corporate business analyst speaking to managers. Focus on KPIs, ROI, risk, compliance, timelines, and decisions. "
        "Summarize crisply, highlight trade‑offs and assumptions, and include next steps."
    ),
    "General Employee": (
        "You are a helpful colleague. Provide clear, plain‑language instructions with minimal jargon. "
        "Offer short steps and tips to complete the task or find the information."
    ),
}

mode = st.radio("Answering mode", ["Hybrid (RAG + LLM)", "Excel SQL"], horizontal=True)
modelname = st.text_input("Gemini model", value="gemini-1.5-flash")

query = st.text_input("Your question", placeholder="e.g., What's the total savings by team in the Excel?")

def sys_prompt_with_citation(persona_key: str) -> str:
    base = persona_prompts.get(persona_key, persona_prompts["General Employee"])
    rules = (
        "Use only the provided context. If the answer is not present, say 'I couldn't find this in the uploaded files.' "
        "Cite sources with filenames in square brackets like [MyDoc.pdf]. "
        "Keep the answer targeted to the persona."
    )
    return base + " " + rules

if st.button("Ask"):
    if not query.strip():
        st.warning("Type a question first.")
    else:
        try:
            if mode == "Hybrid (RAG + LLM)":
                import faiss
                idx_path = os.path.join(INDEX_DIR,'index.faiss')
                meta_path = os.path.join(INDEX_DIR,'meta.pkl')
                if not (os.path.exists(idx_path) and os.path.exists(meta_path)):
                    st.error("Index not found. Upload files and click (Re)build Index first.")
                else:
                    index = faiss.read_index(idx_path)
                    with open(meta_path,'rb') as f:
                        meta = pickle.load(f)
                    reranked = hybrid_search(index, meta["chunks"], query, top_k=8)
                    hits = []
                    for i,score in reranked:
                        hits.append({"score": float(score), "text": meta["chunks"][i], "source": meta["sources"][i]})
                    context = "\\n\\n".join([f"[Source: {h['source']}]\\n{h['text']}" for h in hits])

                    sys_prompt = sys_prompt_with_citation(persona)
                    user_prompt = f"Question: {query}\\n\\nContext:\\n{context}\\n\\nProvide the answer with citations."
                    answer = gemini_chat_text(system_prompt=sys_prompt, user_prompt=user_prompt, model=modelname)
                    st.subheader("Answer")
                    st.write(answer)
                    with st.expander("Top context passages"):
                        for h in hits:
                            st.markdown(f"- **{h['source']}** (rerank={h['score']:.3f})\\n\\n{h['text'][:700]}...")

            else:  # Excel SQL
                excel_paths = [os.path.join(UPLOAD_DIR, p) for p in os.listdir(UPLOAD_DIR)
                               if pathlib.Path(p).suffix.lower() in (".xlsx",".xls")]
                if not excel_paths:
                    st.error("No Excel files uploaded. Upload .xlsx/.xls and try again.")
                else:
                    con = duckdb.connect(database=':memory:')
                    table_map = excel_to_duckdb(con, excel_paths)
                    schema_describe = []
                    for t, origin in table_map.items():
                        df = con.sql(f"SELECT * FROM {t} LIMIT 5").df()
                        schema_describe.append(f"Table {t} (from {origin}) Columns: {', '.join(map(str, df.columns))}")
                    sys_prompt = (
                        "You output only a valid DuckDB SQL query. No backticks, no explanations."
                    )
                    prompt = f\"\"\"
Available tables (with sample columns):
{chr(10).join(schema_describe)}

User question: {query}

Return ONLY the SQL:
\"\"\"
                    sql = gemini_chat_text(system_prompt=sys_prompt, user_prompt=prompt, model=modelname).strip()
                    if sql.lower().startswith("sql"):
                        sql = sql.split("\\n",1)[1] if "\\n" in sql else ""
                    st.code(sql, language="sql")
                    try:
                        df = con.sql(sql).df()
                        st.dataframe(df)
                        preview = df.head(10).to_markdown(index=False)
                        # Persona-aware summary
                        summary_prompt = f"SQL was:\\n{sql}\\n\\nHere is a small sample of the result (markdown table):\\n{preview}"
                        summary = gemini_chat_text(system_prompt=persona_prompts.get(persona, persona_prompts["General Employee"]),
                                                   user_prompt=summary_prompt, model=modelname)
                        st.subheader("Summary")
                        st.write(summary)
                    except Exception as e:
                        st.error(f"SQL execution failed: {e}")
        except Exception as e:
            st.error("Something went wrong. See details in the console.")
            st.exception(e)

st.sidebar.markdown("---")
if st.sidebar.button("Clear indexes"):
    shutil.rmtree(INDEX_DIR, ignore_errors=True)
    os.makedirs(INDEX_DIR, exist_ok=True)
    st.sidebar.success("Indexes cleared.")

st.caption("Gemini 1.5 (free API) • Personas • BM25 + Dense + Cross-Encoder rerank • DuckDB for Excel SQL • OCR optional")
""".strip()
open(f"{base}/app/streamlit_app.py","w").write(streamlit_app_py)

# Zip
zip_path = "/mnt/data/rag_pdf_excel_gemini_persona.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.relpath(full, base)
            z.write(full, arc)

zip_path
