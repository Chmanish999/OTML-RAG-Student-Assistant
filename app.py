import sys
from pathlib import Path

from flask import Flask, render_template, request

BASE_DIR = Path(__file__).resolve().parent
RAG_DIR = BASE_DIR / "rag"

# Allow app.py to import files from rag folder
sys.path.insert(0, str(RAG_DIR))

from retrieve import retrieve
from answer_local import make_short_answer
from answer_gemini import generate_gemini_answer


app = Flask(__name__)


def get_unique_sources(retrieved_results):
    """Return unique retrieved sources for display."""
    unique_sources = []
    seen = set()

    for score, chunk in retrieved_results:
        source_key = (
            chunk.get("practical_no"),
            chunk.get("topic_name"),
            chunk.get("source_file"),
        )

        if source_key in seen:
            continue

        seen.add(source_key)

        unique_sources.append({
            "practical_no": chunk.get("practical_no"),
            "topic_name": chunk.get("topic_name"),
            "source_type": chunk.get("source_type"),
            "source_file": chunk.get("source_file"),
            "repository_url": chunk.get("repository_url"),
            "score": score,
        })

    return unique_sources


def answer_question(question):
    """Retrieve OTML context and generate Gemini answer with local fallback."""
    retrieved_results = retrieve(question, top_k=3)
    sources = get_unique_sources(retrieved_results)

    if not retrieved_results:
        return {
            "answer": "This topic is not covered in the provided OTML Module 1 and practical material.",
            "sources": [],
            "mode": "Out of syllabus"
        }

    try:
        answer = generate_gemini_answer(question, retrieved_results)
        mode = "Gemini RAG Answer"

    except Exception:
        local_result = make_short_answer(question, retrieved_results)
        answer = local_result["answer"]
        mode = "Local fallback answer"

    return {
        "answer": answer,
        "sources": sources,
        "mode": mode
    }


@app.route("/", methods=["GET", "POST"])
def index():
    question = ""
    answer = None
    sources = []
    mode = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if question:
            result = answer_question(question)
            answer = result["answer"]
            sources = result["sources"]
            mode = result["mode"]
        else:
            answer = "Please enter an OTML question."
            mode = "Input required"

    return render_template(
        "index.html",
        question=question,
        answer=answer,
        sources=sources,
        mode=mode
    )


if __name__ == "__main__":
    app.run(debug=True)