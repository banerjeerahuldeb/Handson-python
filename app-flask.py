from flask import Flask, request, render_template_string
from utils.parser import extract_text
from utils.embedder import chunk_text, embed_chunks
from utils.faiss_helper import build_index, search_index
from utils.llm_handler import get_response

import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

html = '''
<!DOCTYPE html>
<html>
<body>
  <h2>Upload Document</h2>
  <form action="/ask" method="post" enctype="multipart/form-data">
    <input type="file" name="file"><br><br>
    <label>Question:</label><br>
    <input type="text" name="question"><br><br>
    <label>LLM Mode:</label>
    <select name="mode">
      <option value="offline">Offline (LLaMA)</option>
      <option value="online">Online (OpenAI)</option>
    </select><br><br>
    <input type="submit" value="Ask">
  </form>
</body>
</html>
'''

@app.route("/", methods=["GET"])
def home():
    return render_template_string(html)

@app.route("/ask", methods=["POST"])
def ask():
    file = request.files["file"]
    question = request.form["question"]
    mode = request.form["mode"]
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    text = extract_text(filepath)
    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)
    index = build_index(embeddings)
    context = search_index(index, embeddings, chunks, question)

    answer = get_response(question, context, mode)
    return f"<h2>Answer:</h2><p>{answer}</p><br><a href='/'>Back</a>"

if __name__ == "__main__":
    app.run(debug=True)
  
