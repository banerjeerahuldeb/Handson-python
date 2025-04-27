import gradio as gr
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, pipeline
import os

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
QA_MODEL = "distilbert-base-cased-distilled-squad"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MAX_CONTEXTS = 3  # Reduce if RAM constrained

class DocumentQA:
    def __init__(self):
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        
        # Initialize DistilBERT QA system
        self.tokenizer = AutoTokenizer.from_pretrained(QA_MODEL)
        self.model = AutoModelForQuestionAnswering.from_pretrained(QA_MODEL)
        self.qa_pipeline = pipeline(
            "question-answering",
            model=self.model,
            tokenizer=self.tokenizer,
            device=-1  # Force CPU usage
        )
        
    def load_documents(self, file_path):
        """Load documents from directory"""
        loaders = {
            ".pdf": "pypdf",
            ".docx": "docx",
            ".pptx": "pptx"
        }
        loader = DirectoryLoader(file_path, glob="**/*", loader_kwargs=loaders)
        return loader.load()
    
    def create_vector_store(self, documents):
        """Process documents into vector store"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        texts = text_splitter.split_documents(documents)
        return Chroma.from_documents(
            texts,
            self.embeddings,
            persist_directory="./chroma_db"
        )
    
    def ask_question(self, file_path, question):
        """Main QA workflow"""
        # Load and process documents
        documents = self.load_documents(file_path)
        db = self.create_vector_store(documents)
        
        # Retrieve relevant contexts
        retriever = db.as_retriever(search_kwargs={"k": MAX_CONTEXTS})
        contexts = [doc.page_content for doc in retriever.get_relevant_documents(question)]
        
        # Get answers from all contexts
        answers = []
        for context in contexts:
            try:
                result = self.qa_pipeline(question=question, context=context)
                answers.append({
                    "answer": result["answer"],
                    "score": result["score"],
                    "context": context
                })
            except:
                continue
        
        if not answers:
            return "No answer found in documents"
        
        # Return best answer
        best_answer = max(answers, key=lambda x: x["score"])
        return f"Answer: {best_answer['answer']}\n\nConfidence: {best_answer['score']:.2f}"

# Gradio Interface
def gradio_interface(file_path, question):
    qa_system = DocumentQA()
    return qa_system.ask_question(file_path, question)

iface = gr.Interface(
    fn=gradio_interface,
    inputs=[
        gr.Textbox(label="Path to documents directory"),
        gr.Textbox(label="Your question")
    ],
    outputs=gr.Textbox(label="Answer"),
    title="Offline Document Q&A with DistilBERT",
    description="Upload documents to a directory and ask questions!"
)

if __name__ == "__main__":
    iface.launch(server_name="127.0.0.1")  # For offline use
