from llama_cpp import Llama
import openai
import os

# Set your OpenAI key in environment variable or here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the offline model lazily (on first use)
llama = None

def load_llama_model():
    global llama
    if llama is None:
        llama = Llama(
            model_path="models/llama-2-7b-chat.Q4_K_M.gguf", 
            n_ctx=1024,
            n_threads=4,
            n_batch=1
        )
    return llama

def get_response(question, context, mode="offline"):
    prompt = f"""[INST] <<SYS>>
You are a helpful assistant. Use the context provided to answer the user's question concisely and accurately.
<</SYS>>

Context:
{context}

Question:
{question}
[/INST]"""

    try:
        if mode == "offline":
            model = load_llama_model()
            response = model(prompt, stop=["</s>"])
            return response["choices"][0]["text"].strip()

        elif mode == "online":
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're a helpful assistant."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
                ]
            )
            return response.choices[0].message.content.strip()
        else:
            return "Invalid LLM mode selected."

    except Exception as e:
        return f"Error generating response: {str(e)}"
