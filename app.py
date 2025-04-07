import streamlit as st
import os
import tempfile
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.llms import OpenAI, HuggingFacePipeline
from langchain.chains import RetrievalQA
from transformers import pipeline

# --- CONFIG ---

st.set_page_config(page_title="RAG QnA with Summary")
st.title("RAG QnA App with Summarization & Local LLMs")

llm_option = st.selectbox("Choose LLM:", ["OpenAI", "Local (Mistral)"])
summarize_opt = st.checkbox("Summarize Document(s)")

# Upload
uploaded_files = st.file_uploader("Upload PDF or DOCX files", type=["pdf", "docx"], accept_multiple_files=True)
query = st.text_input("Ask a question about the document(s)")

# --- PROCESSING ---
def load_files(files):
    docs = []
    for f in files:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(f.read())
            path = tmp.name

        if f.name.endswith(".pdf"):
            loader = PyPDFLoader(path)
        elif f.name.endswith(".docx"):
            loader = Docx2txtLoader(path)
        else:
            continue

        docs.extend(loader.load())
    return docs

def summarize_docs(texts, model_name="facebook/bart-large-cnn"):
    summarizer = pipeline("summarization", model=model_name)
    chunks = [t.page_content for t in texts][:3]  # Limit summary to first few chunks
    summary = "\n\n".join([summarizer(chunk, max_length=150, min_length=40, do_sample=False)[0]['summary_text'] for chunk in chunks])
    return summary

# --- MAIN ---
if uploaded_files:
    all_docs = load_files(uploaded_files)
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_docs = splitter.split_documents(all_docs)

    if summarize_opt:
        st.subheader("Summary")
        with st.spinner("Generating summary..."):
            summary = summarize_docs(split_docs)
            st.write(summary)

    # Embeddings
    embeddings = (
        OpenAIEmbeddings() if llm_option == "OpenAI"
        else HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )
    db = FAISS.from_documents(split_docs, embeddings)

    # LLM choice
    if llm_option == "OpenAI":
        os.environ["OPENAI_API_KEY"] = "your-openai-key"
        llm = OpenAI(temperature=0)
    else:
        st.info("Loading local model... this may take 10–20 seconds.")
        pipe = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1", device_map="auto", max_new_tokens=256)
        llm = HuggingFacePipeline(pipeline=pipe)

    # QA Chain with retrieval (RAG)
    retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, chain_type="stuff")

    # Query
    if query:
        with st.spinner("Thinking..."):
            answer = qa_chain.run(query)
        st.subheader("Answer")
        st.write(answer)
