from pathlib import Path
from urllib.parse import quote
import csv
import requests
import nbformat


BASE_DIR = Path(__file__).resolve().parents[1]

SOURCE_CSV = BASE_DIR / "data" / "raw" / "otml_module1_sources.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"


def clean_text(text):
    """Clean unnecessary spacing and encoding artifacts."""
    replacements = {
        "\xa0": " ",
        "Â": "",
        "\u200b": "",
        "\r": "\n",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def parse_github_url(repo_url):
    """
    Convert:
    https://github.com/Chmanish999/Repo-Name
    into:
    owner = Chmanish999
    repo = Repo-Name
    """
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]
    return owner, repo


def get_default_branch(owner, repo):
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    return response.json().get("default_branch", "main")


def get_repo_tree(owner, repo, branch):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    return response.json().get("tree", [])


def download_raw_file(owner, repo, branch, file_path):
    encoded_path = quote(file_path, safe="/")
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}"

    response = requests.get(raw_url, timeout=30)
    response.raise_for_status()
    return response.text


def find_readme_file(tree):
    """Prefer root README.md, otherwise search any README file."""
    files = [item["path"] for item in tree if item.get("type") == "blob"]

    for file_path in files:
        if file_path.lower() == "readme.md":
            return file_path

    for file_path in files:
        if file_path.lower().endswith("readme.md"):
            return file_path

    return None


def find_notebook_file(tree, expected_notebook):
    """Find expected notebook; if not found, choose first available .ipynb."""
    files = [item["path"] for item in tree if item.get("type") == "blob"]

    expected_lower = expected_notebook.lower()

    for file_path in files:
        if Path(file_path).name.lower() == expected_lower:
            return file_path

    for file_path in files:
        if file_path.lower().endswith(".ipynb"):
            return file_path

    return None


def extract_notebook_text(notebook_content):
    """Extract markdown cells and useful code cells from notebook."""
    notebook = nbformat.reads(notebook_content, as_version=4)

    extracted = []

    for index, cell in enumerate(notebook.cells, start=1):
        cell_type = cell.get("cell_type", "")
        source = cell.get("source", "").strip()

        if not source:
            continue

        if cell_type == "markdown":
            extracted.append(f"\n--- Markdown Cell {index} ---\n{source}")

        elif cell_type == "code":
            code_lines = source.splitlines()

            # Keep code, but avoid making notes too long
            limited_code = "\n".join(code_lines[:60])

            extracted.append(
                f"\n--- Code Cell {index} ---\n"
                f"{limited_code}"
            )

    return clean_text("\n".join(extracted))


def process_repository(row):
    practical_no = row["Practical_No"]
    topic_name = row["Topic_Name"]
    repo_url = row["Repository_URL"]
    expected_notebook = row["Notebook_File"]
    related_ppt = row["Related_PPT_Section"]
    keywords = row["Keywords"]

    owner, repo = parse_github_url(repo_url)

    print(f"\nProcessing {practical_no}: {topic_name}")
    print(f"Repository: {repo_url}")

    branch = get_default_branch(owner, repo)
    tree = get_repo_tree(owner, repo, branch)

    readme_path = find_readme_file(tree)
    notebook_path = find_notebook_file(tree, expected_notebook)

    readme_text = ""
    notebook_text = ""

    if readme_path:
        print(f"README found: {readme_path}")
        readme_text = download_raw_file(owner, repo, branch, readme_path)
    else:
        print("README not found.")

    if notebook_path:
        print(f"Notebook found: {notebook_path}")
        notebook_content = download_raw_file(owner, repo, branch, notebook_path)
        notebook_text = extract_notebook_text(notebook_content)
    else:
        print("Notebook not found.")

    final_text = f"""
============================================================
{practical_no}: {topic_name}
============================================================

Repository URL:
{repo_url}

Related PPT Section:
{related_ppt}

Keywords:
{keywords}

============================================================
README CONTENT
============================================================

{clean_text(readme_text)}

============================================================
NOTEBOOK CONTENT
============================================================

{notebook_text}
"""

    practical_number = practical_no.lower().replace(" ", "")
    output_file = OUTPUT_DIR / f"{practical_number}_notes.txt"

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(clean_text(final_text))

    print(f"Saved: {output_file}")


def main():
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_CSV}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SOURCE_CSV, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get("Use_in_RAG", "").strip().lower() == "yes":
                process_repository(row)

    print("\nAll GitHub practical sources extracted successfully.")


if __name__ == "__main__":
    main()