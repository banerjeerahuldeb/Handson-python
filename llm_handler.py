from llama_cpp import Llama
import openai
import os

# Set your OpenAI key here or use an environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

llama = Llama(
    model_path="models/llama-2-7b.Q4_K_M.gguf", 
    n_ctx=1024,
    n_threads=4
)

def get_response(question, context, mode):
    prompt = f"Answer the question based on the context:\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    if mode == "offline":
        return llama(prompt)["choices"][0]["text"]
    else:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content
