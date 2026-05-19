from pathlib import Path
import json
import re
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_FILE = BASE_DIR / "data" / "chunks" / "otml_module1_chunks.json"

TOP_K = 5
MIN_SCORE = 10


STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "of", "in", "on", "for", "to",
    "and", "or", "with", "by", "from", "how", "why", "explain", "define",
    "give", "me", "about", "using", "use", "does", "do", "please"
}


TOPIC_ALIASES = {
    "Practical 1": [
        "data models learning", "data", "features", "labels",
        "supervised learning", "experience task performance"
    ],
    "Practical 2": [
        "model fitting", "error measurement", "loss", "mse",
        "prediction error", "accuracy", "evaluation"
    ],
    "Practical 3": [
        "empirical risk minimization", "empirical risk", "erm",
        "true risk", "training error", "generalization"
    ],
    "Practical 4": [
        "parameter estimation", "estimator", "mle",
        "maximum likelihood", "lse", "least squares", "map"
    ],
    "Practical 5": [
        "gradient descent", "learning rate", "gradient",
        "parameter update", "iteration"
    ],
    "Practical 6": [
        "lagrange multiplier", "lagrange multipliers",
        "lagrangian", "constrained optimization",
        "equality constraint", "constraint"
    ],
    "Practical 7": [
        "convex optimization", "convex function",
        "global minimum", "local minimum", "feasible region"
    ],
    "Practical 8": [
        "probabilistic modelling", "probabilistic modeling",
        "inference", "uncertainty", "joint probability",
        "conditional probability"
    ],
    "Practical 9": [
        "directed graphical model", "directed graphical models",
        "dgm", "dag", "bayesian network",
        "graphical model", "nodes", "edges",
        "parent child", "marginal inference"
    ],
}


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text):
    words = normalize_text(text).split()
    return [word for word in words if word not in STOPWORDS and len(word) > 2]


def load_chunks():
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_FILE}")

    with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def detect_target_practical(query):
    normalized_query = normalize_text(query)

    best_practical = None
    best_hits = 0

    for practical_no, aliases in TOPIC_ALIASES.items():
        hits = 0

        for alias in aliases:
            alias_norm = normalize_text(alias)

            if alias_norm in normalized_query:
                hits += 3
            else:
                alias_words = alias_norm.split()
                if all(word in normalized_query for word in alias_words):
                    hits += 2

        if hits > best_hits:
            best_hits = hits
            best_practical = practical_no

    return best_practical


def score_chunk(query, chunk):
    query_tokens = tokenize(query)
    target_practical = detect_target_practical(query)

    chunk_text = normalize_text(chunk.get("text", ""))
    topic_name = normalize_text(chunk.get("topic_name", ""))
    practical_no = chunk.get("practical_no", "")
    source_file = normalize_text(chunk.get("source_file", ""))
    source_type = chunk.get("source_type", "")

    metadata_text = normalize_text(" ".join([
        chunk.get("topic_name", ""),
        chunk.get("related_ppt_section", ""),
        chunk.get("keywords", ""),
        chunk.get("source_file", ""),
        chunk.get("practical_no", "")
    ]))

    score = 0

    # Basic token matching
    for token in query_tokens:
        if token in chunk_text:
            score += 2

        # Metadata is more reliable for GitHub practical files
        if source_type == "GitHub Practical" and token in metadata_text:
            score += 5

    # Strong boost if query clearly belongs to a particular practical
    if target_practical:
   	 if practical_no == target_practical:
        	score += 90

    # Strongly prefer exact practical repository over PPT
    if practical_no == target_practical and source_type == "GitHub Practical":
        score += 80

    # PPT is useful as theory support, but practical should rank first
    if source_type == "Module PPT":
        aliases = TOPIC_ALIASES.get(target_practical, [])
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm in chunk_text:
                score += 10

    # Phrase-level matching
    normalized_query = normalize_text(query)

    for practical_no_key, aliases in TOPIC_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_text(alias)

            if alias_norm in normalized_query:
                if alias_norm in chunk_text:
                    score += 25

                if source_type == "GitHub Practical" and alias_norm in metadata_text:
                    score += 35

    # Reduce score of generic PPT overview chunks unless actual text contains the concept
    if source_type == "Module PPT" and target_practical:
        aliases = TOPIC_ALIASES.get(target_practical, [])
        has_actual_topic_text = any(
            normalize_text(alias) in chunk_text for alias in aliases
        )

        if not has_actual_topic_text:
            score -= 25

    return score


def retrieve(query, top_k=TOP_K):
    chunks = load_chunks()
    scored_chunks = []

    for chunk in chunks:
        score = score_chunk(query, chunk)

        if score >= MIN_SCORE:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    return scored_chunks[:top_k]


def print_results(query, results):
    print("\n============================================================")
    print("QUERY")
    print("============================================================")
    print(query)

    if not results:
        print("\nNo relevant OTML Module 1 content found.")
        return

    print("\n============================================================")
    print("TOP RETRIEVED CHUNKS")
    print("============================================================")

    for rank, (score, chunk) in enumerate(results, start=1):
        print(f"\nResult {rank}")
        print("-" * 60)
        print(f"Score: {score}")
        print(f"Source File: {chunk.get('source_file')}")
        print(f"Source Type: {chunk.get('source_type')}")
        print(f"Practical No.: {chunk.get('practical_no')}")
        print(f"Topic: {chunk.get('topic_name')}")
        print(f"Related PPT Section: {chunk.get('related_ppt_section')}")
        print(f"Repository URL: {chunk.get('repository_url')}")

        preview = chunk.get("text", "")[:350]
        print("\nShort Preview:")
        print(preview)
        print("-" * 60)


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter your OTML question: ")

    results = retrieve(query, top_k=TOP_K)
    print_results(query, results)


if __name__ == "__main__":
    main()