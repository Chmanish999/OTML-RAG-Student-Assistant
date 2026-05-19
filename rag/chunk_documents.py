from pathlib import Path
import csv
import json
import re


BASE_DIR = Path(__file__).resolve().parents[1]

SOURCE_CSV = BASE_DIR / "data" / "raw" / "otml_module1_sources.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNKS_DIR = BASE_DIR / "data" / "chunks"
OUTPUT_JSON = CHUNKS_DIR / "otml_module1_chunks.json"


CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250


def clean_text(text):
    """Clean extracted text before chunking."""
    replacements = {
        "\xa0": " ",
        "Â": "",
        "\u200b": "",
        "\r": "\n",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def load_source_metadata():
    """Load practical metadata from source CSV."""
    metadata = {}

    with open(SOURCE_CSV, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            practical_no = row["Practical_No"].strip()
            key = practical_no.lower().replace(" ", "")

            metadata[key] = {
                "practical_no": practical_no,
                "topic_name": row["Topic_Name"].strip(),
                "repository_url": row["Repository_URL"].strip(),
                "related_ppt_section": row["Related_PPT_Section"].strip(),
                "keywords": row["Keywords"].strip(),
                "source_type": "GitHub Practical",
            }

    return metadata


def split_text_into_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    text = clean_text(text)

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Try to break at paragraph or sentence boundary
            paragraph_break = text.rfind("\n\n", start, end)
            sentence_break = text.rfind(". ", start, end)

            if paragraph_break > start + 500:
                end = paragraph_break
            elif sentence_break > start + 500:
                end = sentence_break + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = max(end - overlap, end)

    return chunks


def get_file_metadata(file_path, source_metadata):
    """Create metadata for PPT and practical files."""
    file_name = file_path.name

    if file_name == "module1_otml_notes.txt":
        return {
            "practical_no": "Theory Source",
            "topic_name": "OTML Module 1 PPT",
            "repository_url": "Not applicable",
            "related_ppt_section": "Complete Module 1 PPT",
            "keywords": "OTML; Module 1; model fitting; ERM; parameter estimation; gradient descent; convex optimization; probabilistic modelling; directed graphical models",
            "source_type": "Module PPT",
        }

    match = re.search(r"practical(\d+)_notes\.txt", file_name)

    if match:
        practical_key = f"practical{match.group(1)}"
        return source_metadata.get(
            practical_key,
            {
                "practical_no": practical_key,
                "topic_name": "Unknown Practical",
                "repository_url": "Unknown",
                "related_ppt_section": "Unknown",
                "keywords": "",
                "source_type": "GitHub Practical",
            },
        )

    return {
        "practical_no": "Unknown",
        "topic_name": "Unknown",
        "repository_url": "Unknown",
        "related_ppt_section": "Unknown",
        "keywords": "",
        "source_type": "Unknown",
    }


def main():
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_CSV}")

    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Processed directory not found: {PROCESSED_DIR}")

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    source_metadata = load_source_metadata()

    all_chunks = []
    chunk_counter = 1

    text_files = sorted(PROCESSED_DIR.glob("*.txt"))

    if not text_files:
        raise FileNotFoundError("No processed .txt files found.")

    for file_path in text_files:
        print(f"Chunking file: {file_path.name}")

        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        metadata = get_file_metadata(file_path, source_metadata)
        chunks = split_text_into_chunks(text)

        for local_index, chunk_text in enumerate(chunks, start=1):
            chunk_record = {
                "chunk_id": f"otml_m1_chunk_{chunk_counter:04d}",
                "source_file": file_path.name,
                "source_type": metadata["source_type"],
                "practical_no": metadata["practical_no"],
                "topic_name": metadata["topic_name"],
                "related_ppt_section": metadata["related_ppt_section"],
                "repository_url": metadata["repository_url"],
                "keywords": metadata["keywords"],
                "chunk_number_in_file": local_index,
                "text": chunk_text,
                "char_count": len(chunk_text),
            }

            all_chunks.append(chunk_record)
            chunk_counter += 1

        print(f"Created {len(chunks)} chunks from {file_path.name}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(all_chunks, file, ensure_ascii=False, indent=2)

    print("\nRAG chunk creation completed successfully.")
    print(f"Total source files processed: {len(text_files)}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Output file: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()