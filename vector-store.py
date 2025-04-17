import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text, max_length=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_length):
        chunk = " ".join(words[i:i+max_length])
        chunks.append(chunk)
    return chunks

def build_faiss_index(chunks):
    embeddings = embed_model.encode(chunks)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    return index, chunks

def get_top_k_chunks(question, chunks, index, k=3):
    q_embedding = embed_model.encode([question])
    D, I = index.search(np.array(q_embedding), k)
    return [chunks[i] for i in I[0]]
