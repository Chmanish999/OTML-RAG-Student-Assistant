import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from retrieve import retrieve
from answer_local import make_short_answer, print_final_answer


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def build_context(retrieved_results, max_chars_per_chunk=8000):
    """
    Prepare retrieved OTML chunks as context for Gemini.
    Larger context is used so Gemini can generate exam-oriented answers.
    """
    context_blocks = []

    for index, (score, chunk) in enumerate(retrieved_results, start=1):
        source_info = (
            f"Source {index}\n"
            f"Score: {score}\n"
            f"Source Type: {chunk.get('source_type')}\n"
            f"Practical No.: {chunk.get('practical_no')}\n"
            f"Topic: {chunk.get('topic_name')}\n"
            f"Source File: {chunk.get('source_file')}\n"
            f"Repository URL: {chunk.get('repository_url')}\n"
        )

        text = chunk.get("text", "")[:max_chars_per_chunk]

        context_blocks.append(
            f"{source_info}\n"
            f"Content:\n{text}"
        )

    separator = "\n\n" + ("-" * 80) + "\n\n"
    return separator.join(context_blocks)


def build_prompt(question, context):
    """
    Create strict exam-oriented RAG prompt for Gemini.
    """
    return f"""
You are an OTML Student Assistant for undergraduate students.

You must answer ONLY using the provided OTML context.
Do not use outside knowledge.
Do not invent information.
Use clear, formal, academic, classroom-friendly language.
Do not use Markdown formatting symbols such as **, ##, `, or triple backticks.

The answer must be suitable for handwritten university examination preparation.
Do not give a very short answer.
Do not answer only in 2 or 3 lines.
The answer must be descriptive enough for a 5-mark to 10-mark question.

If the answer is not available in the provided OTML context, reply exactly:
"This topic is not covered in the provided OTML Module 1 and practical material."

Student Question:
{question}

Provided OTML Context:
{context}

Required Answer Format:

Answer:

1. Definition
Write a clear and direct definition of the concept.

2. Explanation
Explain the concept in simple academic language suitable for undergraduate students.

3. Role in Optimization Techniques in Machine Learning
Explain why this concept is important in OTML or machine learning optimization.

4. Working / Key Idea
Explain how the concept works, or describe its main idea step by step.

5. Important Points
Give 4 to 6 important points in bullet form.

6. Example
Give a small example from the provided context if available.

7. Conclusion
End with a short conclusion that can be written in an exam.

Length Requirement:
Write at least 300 words if enough context is available.
For broad theory questions, write 350 to 500 words.
Avoid overly short answers.

Sources Used:
Mention the Practical number/topic and/or Module PPT source used.
"""

def clean_gemini_output(text):
    """
    Remove Markdown formatting symbols from Gemini output
    so answers appear clean for classroom/exam use.
    """
    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("```text", "")
    text = text.replace("```python", "")
    text = text.replace("```", "")
    text = text.replace("`", "")

    return text.strip()
def generate_gemini_answer(question, retrieved_results):
    """
    Generate answer from Gemini using retrieved OTML context.
    """
    if not retrieved_results:
        return (
            "Answer:\n"
            "This topic is not covered in the provided OTML Module 1 and practical material.\n\n"
            "Sources Used:\n"
            "- No valid OTML source found."
        )

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Please add it to your .env file locally "
            "or configure it as a Secret Manager environment variable on Cloud Run."
        )

    context = build_context(retrieved_results)
    prompt = build_prompt(question, context)

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return response.text


def print_unique_retrieved_sources(retrieved_results):
    """
    Print unique retrieved local sources only once.
    """
    print("\nRetrieved Sources Checked Locally:")

    if not retrieved_results:
        print("No valid OTML source found.")
        return

    seen_sources = set()
    unique_index = 1

    for score, chunk in retrieved_results:
        source_key = (
            chunk.get("practical_no"),
            chunk.get("topic_name"),
            chunk.get("source_file"),
        )

        if source_key in seen_sources:
            continue

        seen_sources.add(source_key)

        print(
            f"{unique_index}. {chunk.get('practical_no')} - "
            f"{chunk.get('topic_name')} "
            f"({chunk.get('source_file')})"
        )

        unique_index += 1


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Enter your OTML question: ")

    retrieved_results = retrieve(question, top_k=7)

    print("\n============================================================")
    print("OTML STUDENT ASSISTANT - GEMINI RAG ANSWER")
    print("============================================================")

    print("\nQuestion:")
    print(question)

    print("\nGemini Answer:")

    try:
        answer = generate_gemini_answer(question, retrieved_results)
        print(answer)

    except Exception as error:
        print("Gemini failed. Error details:")
        print(error)
        print("\nFalling back to local template-based answer.\n")

        local_result = make_short_answer(question, retrieved_results)
        print_final_answer(question, local_result)

    print_unique_retrieved_sources(retrieved_results)


if __name__ == "__main__":
    main()