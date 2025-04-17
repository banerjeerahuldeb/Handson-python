import streamlit as st
from llm_handler import stream_response_offline, get_response_online
from utils import extract_text_from_pdf

st.set_page_config(page_title="QnA from Document", layout="centered")
st.title("QnA from Document (Offline LLaMA / Online Gemini)")

mode = st.radio("Select LLM Mode", ["Offline (LLaMA)", "Online (Gemini)"], horizontal=True)

uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])
question = st.text_input("Ask a question based on the document")

if uploaded_file:
    context = extract_text_from_pdf(uploaded_file)
    st.success("Document loaded successfully!")

    if question and context:
        st.subheader("Answer:")
        response_area = st.empty()
        if mode == "Offline (LLaMA)":
            result = ""
            for chunk in stream_response_offline(question, context):
                result += chunk
                response_area.markdown(result)
        else:
            with st.spinner("Fetching answer from Gemini..."):
                result = get_response_online(question, context)
                response_area.markdown(result)
