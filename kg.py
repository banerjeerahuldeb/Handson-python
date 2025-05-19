import csv
import re
import gradio as gr
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer

# 1. Create and load employee data
def initialize_data():
    CSV_CONTENT = """id,name,role,department,skills,reports_to
1,Alice,Developer,IT,"Azure, .NET, C#",Bob
2,Bob,Manager,IT,"Cloud Architecture, Project Management",Carol
3,Carol,CTO,Executive,"Leadership, Strategy",NULL
4,David,Data Engineer,IT,"Python, SQL, ETL",Bob
5,Eve,Marketing Lead,Marketing,"SEO, Campaign Management",Carol
6,Frank,Developer,IT,"Java, Oracle, Spring Boot",Bob
"""
    with open("employees.csv", "w") as f:
        f.write(CSV_CONTENT)

def load_employees():
    employees = []
    with open("employees.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            employees.append({
                'name': row['name'],
                'skills': [s.strip() for s in row['skills'].split(",")],
                'department': row['department']
            })
    return employees

initialize_data()
employees = load_employees()
employee_names = [e['name'] for e in employees]

# 2. Initialize LLM
model = GPT2LMHeadModel.from_pretrained("gpt2")
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device=-1,
    temperature=0.01,
)

# 3. Query processing
def direct_skill_lookup(skill):
    skill = skill.lower()
    return [e['name'] for e in employees if any(skill in s.lower() for s in e['skills'])]

def process_question(question):
    # Direct skill lookup
    skill_match = re.search(r"(skilled in|knows|with|who knows)\s+(.+?)(\?|$)", question, re.I)
    if skill_match:
        skill = skill_match.group(2).strip()
        results = direct_skill_lookup(skill)
        if results:
            return ", ".join(results)
    
    # LLM fallback
    context = "\n".join([f"{e['name']} ({e['department']}): {', '.join(e['skills'])}" for e in employees])
    prompt = f"""Answer using ONLY this data:
{context}

Format answer as: names separated by commas
Question: {question}
Answer:"""
    
    response = generator(
        prompt,
        max_length=200,
        num_return_sequences=1,
        pad_token_id=tokenizer.eos_token_id
    )
    
    answer = response[0]['generated_text'].split("Answer:")[-1].strip()
    valid_names = [name.strip() for name in re.split(r",|\sand\s", answer) 
                  if name.strip() in employee_names]
    
    return ", ".join(valid_names) if valid_names else "No matches found"

# 4. Gradio UI
def show_csv():
    with open("employees.csv", "r") as f:
        return f.read()

with gr.Blocks(title="Employee Knowledge Graph") as demo:
    gr.Markdown("# 🧑💼 Employee Skill Finder")
    gr.Markdown("Query employee skills using our knowledge graph")
    
    with gr.Row():
        with gr.Column():
            csv_view = gr.Textbox(label="Employee Database", value=show_csv, 
                               interactive=False, lines=10)
        with gr.Column():
            question = gr.Textbox(label="Ask a question", placeholder="Who knows Java?")
            answer = gr.Textbox(label="Answer", interactive=False)
            ask_btn = gr.Button("Ask")
    
    with gr.Row():
        gr.Examples(
            examples=[
                ["Who knows Java?"],
                ["List Python developers"],
                ["Who works in Marketing?"],
                ["Find employees with Azure skills"]
            ],
            inputs=question
        )

    ask_btn.click(fn=process_question, inputs=question, outputs=answer)
    demo.load(fn=show_csv, outputs=csv_view)

if __name__ == "__main__":
    demo.launch()
