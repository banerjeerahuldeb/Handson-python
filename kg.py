import csv
import re
from transformers import pipeline, GPT2LMHeadModel, GPT2Tokenizer

# 1. Create Knowledge Base CSV
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

# 2. Knowledge Graph to Text Converter
def csv_to_context(csv_path):
    employees = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            skills = f"Skilled in: {row['skills']}" if row['skills'] else ""
            report = f"Reports to: {row['reports_to']}" if row['reports_to'] != "NULL" else ""
            employees.append(
                f"Employee {row['name']} - {row['role']} ({row['department']}). {skills} {report}"
            )
    return " ".join(employees)

# 3. Initialize Offline LLM (GPT-2)
model = GPT2LMHeadModel.from_pretrained("gpt2")
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
model.eval()  # Reduces memory usage

qa_pipeline = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device=-1  # Force CPU usage
)

# 4. Query Processing with Skill Matching
def get_employees():
    with open("employees.csv", "r") as f:
        return [row["name"] for row in csv.DictReader(f)]

def refine_answer(answer, employees):
    answer_clean = re.sub(r"[^a-zA-Z, ]", "", answer).lower()
    matches = []
    for emp in employees:
        if emp.lower() in answer_clean:
            matches.append(emp)
    return ", ".join(matches) if matches else "No matching employees found"

def answer_question(question):
    kg_context = csv_to_context("employees.csv")
    employees = get_employees()
    
    prompt = f"""Based on this employee database:
{kg_context}
Question: {question}
Answer:"""
    
    response = qa_pipeline(
        prompt,
        max_length=300,
        num_return_sequences=1,
        temperature=0.1,
        pad_token_id=50256
    )
    
    raw_answer = response[0]["generated_text"].split("Answer:")[-1].strip()
    return refine_answer(raw_answer, employees)

# 5. Interactive Interface
if __name__ == "__main__":
    print("Employee Knowledge Graph Q&A\nType 'exit' to quit")
    while True:
        question = input("\nYour question: ")
        if question.lower() in ["exit", "quit"]:
            break
        if not question.strip():
            continue
        print("Answer:", answer_question(question))
