import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def build_index(embeddings):
    dim = embeddings[0].shape[0]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    return index

def search_index(index, embeddings, chunks, question):
    q_emb = model.encode([question])
    D, I = index.search(np.array(q_emb), k=3)
    return "\n".join([chunks[i] for i in I[0]])
