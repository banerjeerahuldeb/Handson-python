
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="IntelliKnow Hub (Prototype)", layout="wide", page_icon="📘")

st.markdown(
    '''
    <style>
    .result-card {padding:16px; border:1px solid rgba(255,255,255,0.1); border-radius:16px; margin-bottom:12px;}
    .pill {display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid rgba(255,255,255,0.15); margin-right:6px; font-size:12px;}
    .source {opacity:0.85;}
    .muted {opacity:0.7;}
    .small {font-size:12px;}
    .title {font-weight:700; font-size:18px;}
    .banner {padding:10px 16px; border-radius:16px; border:1px solid rgba(255,255,255,0.1); background:rgba(127,127,127,0.08);}
    </style>
    ''',
    unsafe_allow_html=True
)

DATA_PATH = Path(__file__).parent / "documents.json"
docs = json.loads(Path(DATA_PATH).read_text())
df = pd.DataFrame(docs)

st.sidebar.title("IntelliKnow Hub")
st.sidebar.caption("AI-Powered Role-Based Knowledge Repository (Demo)")

role = st.sidebar.selectbox(
    "Your Role",
    [
        "EBS Engineer", "EBS Lead",
        "NonEBS Engineer", "Integration Lead",
        "Middleware L1", "Middleware L2",
        "BI Analyst", "Analytics Lead",
        "Hyperion Admin", "Finance Lead",
        "Release Manager",
        "Account Admin"
    ],
    index=0
)

tower_filter = st.sidebar.multiselect(
    "Tower Filter",
    sorted(df["tower"].unique().tolist()),
    default=sorted(df["tower"].unique().tolist())
)

source_filter = st.sidebar.multiselect(
    "Source Filter",
    sorted(df["source"].unique().tolist()),
    default=sorted(df["source"].unique().tolist())
)

st.sidebar.markdown("---")
st.sidebar.caption("📈 Demo telemetry (local only)")
if "query_log" not in st.session_state:
    st.session_state.query_log = []

st.title("📘 IntelliKnow Hub")
st.markdown('<div class="banner">Unified, role-aware knowledge search across SharePoint, Azure DevOps, Teams, and File Shares. (Dummy data)</div>', unsafe_allow_html=True)

colA, colB = st.columns([3, 1])
with colA:
    query = st.text_input("🔎 Ask in natural language (e.g., “Show me EBS refinery safety procedures”)", "")
with colB:
    top_k = st.selectbox("Results", [3, 5, 10, 20], index=1)

def is_allowed(row, user_role: str) -> bool:
    return user_role in row["allowed_roles"]

def run_search(q: str, user_role: str, towers, sources, k: int = 5):
    base = df.copy()
    base = base[base.apply(lambda r: is_allowed(r, user_role), axis=1)]
    base = base[base["tower"].isin(towers) & base["source"].isin(sources)]
    if not q.strip():
        return base.sample(frac=1, random_state=42).head(k)

    corpus = (base["title"] + " " + base["summary"] + " " +
              base["tower"] + " " + base["track"] + " " +
              base["source"] + " " + base["tags"].apply(lambda x: " ".join(x)) + " " +
              base["content"]).tolist()
    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(corpus)
    q_vec = vectorizer.transform([q])
    sims = cosine_similarity(q_vec, X).flatten()
    base = base.copy()
    base["score"] = sims
    base = base.sort_values("score", ascending=False).head(k)
    return base

results = run_search(query, role, tower_filter, source_filter, k=top_k)

if query:
    st.session_state.query_log.append({"ts": time.time(), "role": role, "query": query, "results": results["id"].tolist()})

st.subheader("Results")
if results.empty:
    st.info("No results for current role/filters. Try another role or clear filters.")
else:
    for _, r in results.iterrows():
        with st.container(border=False):
            st.markdown(f'''
            <div class="result-card">
              <div class="title">{r["title"]}</div>
              <div class="small muted">{r["summary"]}</div>
              <div style="margin-top:8px;">
                <span class="pill">{r["tower"]}</span>
                <span class="pill">{r["track"]}</span>
                <span class="pill source">{r["source"]}</span>
                {''.join([f'<span class="pill">{t}</span>' for t in r["tags"]])}
              </div>
              <div class="small muted" style="margin-top:8px;">ID: {r["id"]} • Relevance: {round(float(r.get("score", 0))*100)}%</div>
            </div>
            ''', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1,1,6])
            with c1:
                st.link_button("Open Source", r["url"], use_container_width=True)
            with c2:
                if st.button("Copy Link", key=f"copy_{r['id']}"):
                    st.toast("Link copied to clipboard (demo).")
            with c3:
                fb = st.segmented_control("Feedback", options=["👍 Useful", "👎 Not useful"], key=f"fb_{r['id']}", selection_mode="single")
            st.markdown("")

st.subheader("💬 Conversational Assistant (Demo)")
assistant_q = st.text_input("Ask a follow-up question", key="assistant_q")
if assistant_q:
    grounded = run_search(assistant_q, role, tower_filter, source_filter, k=3)
    if grounded.empty:
        st.warning("I can't answer from your accessible documents. Try a different role or query.")
    else:
        st.success("Here’s a grounded answer based on your accessible documents:")
        snippet = []
        for _, g in grounded.iterrows():
            snippet.append(f"- **{g['title']}** — *{g['summary']}*  \n  Source: {g['source']} • Tower: {g['tower']}  \n  Citation: `{g['url']}`")
        st.markdown("\n".join(snippet))

with st.expander("📊 Usage Analytics (Demo)"):
    log_df = pd.DataFrame(st.session_state.query_log) if st.session_state.query_log else pd.DataFrame(columns=["ts","role","query","results"])
    st.dataframe(log_df, use_container_width=True)
    if not log_df.empty:
        top_queries = log_df["query"].value_counts().head(10).rename_axis("query").reset_index(name="count")
        st.bar_chart(top_queries.set_index("query"))
        st.download_button("Download Query Log (CSV)", data=log_df.to_csv(index=False), file_name="intelliknow_query_log.csv")

st.caption("⚠️ Demo only — RBAC is simulated via role labels; links are placeholders. In production, enforce security trimming with Graph and source permissions.")
