import os, io, pathlib, shutil, pickle
import streamlit as st
from pypdf import PdfReader
import duckdb

# --- local modules (ensure app/__init__.py exists) ---
from app.utils import excel_to_duckdb, excel_to_text
from app.ocr import ocr_pdf
from app.retriever import build_dense_index, hybrid_search
from app.gemini_client import gemini_chat  # you already have a Gemini-only client

# ------- Constants -------
INDEX_DIR = "indexes"
UPLOAD_DIR = "uploads"

# ------- Page / Sidebar -------
st.set_page_config(page_title="RAG Chat Agent (Gemini)", layout="wide")

with st.sidebar:
    st.title("📁 Upload & Index")
    uploaded_files = st.file_uploader(
        "Upload PDFs and/or Excel files (.pdf, .xlsx, .xls)",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True
    )
    use_ocr = st.checkbox("Use OCR for scanned PDFs (slower)", value=False)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear uploads", use_container_width=True):
            shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            st.success("Uploads cleared.")
    with col2:
        if st.button("Clear indexes", use_container_width=True):
            shutil.rmtree(INDEX_DIR, ignore_errors=True)
            os.makedirs(INDEX_DIR, exist_ok=True)
            st.success("Indexes cleared.")

    if st.button("(Re)build Index", type="primary", use_container_width=True):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(INDEX_DIR, exist_ok=True)

        # Save newly uploaded files (if any). If none this time, reuse existing.
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
                    text = "\n".join(full_text).strip()
                    if use_ocr and not text:
                        text = ocr_pdf(path)

                    # simple chunking for the index
                    words = text.split()
                    size, overlap = 180, 30
                    i = 0
                    while i < len(words):
                        ck = " ".join(words[i:i + size]).strip()
                        if ck:
                            chunks.append(ck)
                            sources.append(f"{p.name} (PDF)")
                        i += size - overlap

                elif p.suffix.lower() in (".xlsx", ".xls"):
                    text = excel_to_text(path)
                    words = text.split()
                    size, overlap = 220, 40
                    i = 0
                    while i < len(words):
                        ck = " ".join(words[i:i + size]).strip()
                        if ck:
                            chunks.append(ck)
                            sources.append(f"{p.name} (Excel)")
                        i += size - overlap
            except Exception as e:
                st.error(f"Failed to parse {p.name}: {e}")

        if not chunks:
            st.warning("No content to index. Upload files first.")
        else:
            import faiss
            index, _ = build_dense_index(chunks)
            faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))
            with open(os.path.join(INDEX_DIR, "meta.pkl"), "wb") as f:
                pickle.dump({"chunks": chunks, "sources": sources}, f)
            st.success(f"Indexed {len(chunks)} chunks from {len(saved_paths)} files.")

# ------- Header / Controls -------
st.title("🤖 RAG Chat Agent (Gemini)")

persona = st.selectbox(
    "Persona",
    ["Plant Operator", "Corporate Employee", "General Employee"],
    index=0,
    help="This adjusts tone, structure, and what to emphasize."
)

mode = st.radio(
    "Mode",
    ["Hybrid (RAG + Gemini)", "Excel SQL"],
    horizontal=True
)

# Persona-specific guidance injected into prompts
PERSONA_SYSTEM = {
    "Plant Operator": (
        "You are a plant operator assistant. Be safety-first and action-oriented. "
        "Prefer SOP/checklist style, include warnings and required permits where applicable, "
        "and keep answers grounded in the provided context."
    ),
    "Corporate Employee": (
        "You are a corporate advisor. Focus on KPIs, decisions, risks, compliance, and business impact. "
        "Keep answers structured and grounded in the provided context."
    ),
    "General Employee": (
        "You are a clear and friendly assistant. Explain in plain language and stay concise. "
        "Answer strictly from the provided context."
    ),
}

# ------- Session State for Chat -------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of dicts: {role: "user"|"assistant", "content": str}

def render_history():
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])
            if "citations" in m and m["citations"]:
                st.caption("Sources: " + " • ".join(m["citations"]))

render_history()

# ------- Helpers -------
def load_index_or_warn():
    idx_path = os.path.join(INDEX_DIR, "index.faiss")
    meta_path = os.path.join(INDEX_DIR, "meta.pkl")
    if not (os.path.exists(idx_path) and os.path.exists(meta_path)):
        st.error("Index not found. Upload files and click (Re)build Index first.")
        return None, None
    import faiss
    index = faiss.read_index(idx_path)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    return index, meta

def persona_prefix():
    return PERSONA_SYSTEM.get(persona, PERSONA_SYSTEM["General Employee"])

def answer_with_rag(user_text: str):
    index, meta = load_index_or_warn()
    if index is None:
        return "I can’t find an index yet. Please (Re)build Index from the sidebar.", []

    reranked = hybrid_search(index, meta["chunks"], user_text, top_k=8)
    hits = []
    for i, score in reranked:
        hits.append({
            "score": float(score),
            "text": meta["chunks"][i],
            "source": meta["sources"][i]
        })

    context = "\n\n".join([f"[Source: {h['source']}]\n{h['text']}" for h in hits])

    system = (
        persona_prefix()
        + " Cite sources by filename in [brackets]. "
        + "If the answer is not present in the context, say you cannot find it."
    )
    user_prompt = f"Question: {user_text}\n\nContext:\n{context}\n\nAnswer succinctly with citations."

    reply = gemini_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
    )
    cites = sorted({h["source"].split(" (")[0] for h in hits})
    return reply, cites

def answer_with_sql(user_text: str):
    excel_paths = [
        os.path.join(UPLOAD_DIR, p) for p in os.listdir(UPLOAD_DIR)
        if pathlib.Path(p).suffix.lower() in (".xlsx", ".xls")
    ]
    if not excel_paths:
        return "No Excel files uploaded. Upload .xlsx/.xls and try again.", []

    con = duckdb.connect(database=":memory:")
    table_map = excel_to_duckdb(con, excel_paths)

    schema_describe = []
    for t, origin in table_map.items():
        df = con.sql(f"SELECT * FROM {t} LIMIT 5").df()
        schema_describe.append(f"Table {t} (from {origin}) Columns: {', '.join(map(str, df.columns))}")

    system = (
        persona_prefix()
        + " You must first output ONLY a valid DuckDB SQL query to answer the user's question, no commentary. "
        + "Avoid backticks and code fences."
    )
    prompt = (
        "Return ONLY a valid DuckDB SQL that answers the question. "
        "Available tables and sample schemas:\n"
        + "\n".join(schema_describe)
        + f"\n\nQuestion: {user_text}\nSQL:"
    )

    sql = gemini_chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    ).strip()

    # sanitize common fence prefixes
    low = sql.lower()
    if low.startswith("sql"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else ""

    try:
        df = con.sql(sql).df()
    except Exception as e:
        return f"SQL execution failed: {e}\n\nGenerated SQL:\n{sql}", []

    # Summarize result for the persona
    preview_md = df.head(10).to_markdown(index=False)
    summary = gemini_chat(
        messages=[
            {"role": "system", "content": persona_prefix()},
            {"role": "user", "content": f"Explain the SQL result briefly for the intended audience.\nSQL:\n{sql}\n\nSample rows:\n{preview_md}"}
        ]
    )

    table_files = sorted({p.split(os.sep)[-1] for p in excel_paths})
    reply = f"**SQL Result (first rows shown in app):**\n\n{summary}"
    return reply, table_files

# ------- Chat Input -------
user_text = st.chat_input(
    "Ask your question...",
    max_chars=2000
)

if user_text:
    # show user bubble
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    # agent typing...
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if mode == "Hybrid (RAG + Gemini)":
                reply, citations = answer_with_rag(user_text)
                st.write(reply)
                if citations:
                    st.caption("Sources: " + " • ".join(citations))
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "citations": citations}
                )
            else:
                reply, citations = answer_with_sql(user_text)
                st.write(reply)
                if citations:
                    st.caption("Excel tables: " + " • ".join(citations))
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply, "citations": citations}
                )

st.caption("Gemini chat agent with personas • RAG (BM25 + Dense + Rerank) • Excel SQL via DuckDB • OCR optional")
