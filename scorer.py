import csv
import requests
import os
import re
import time

# Load API key from .env manually
with open(".env") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY"):
            API_KEY = line.strip().split("=", 1)[1]

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={API_KEY}"

HANDBOOK_PATH = "handbook/handbook.md"
TEST_PATH = "tests/test_set.csv"
OUTPUT_PATH = "results/raw_answers.csv"
os.makedirs("results", exist_ok=True)

with open(HANDBOOK_PATH, encoding="utf-8") as f:
    HANDBOOK = f.read()

# Build set of every section number that actually exists in the handbook
def extract_handbook_sections(handbook_text: str) -> set:
    """Pull every section number that actually exists in the handbook."""
    return set(re.findall(r"\b(\d+\.\d+(?:\.\d+)?)\b", handbook_text))

HANDBOOK_SECTIONS = extract_handbook_sections(HANDBOOK)

def check_citations(answer: str, valid_sections: set) -> list:
    """
    Return a list of section numbers cited in the answer that don't exist
    in the handbook. Empty list means all citations are valid.
    """
    cited = re.findall(r"[Ss]ection\s+(\d+\.\d+(?:\.\d+)?)", answer)
    return [s for s in cited if s not in valid_sections]

SYSTEM_PROMPT = """You are an HR policy assistant for MediCore Bangladesh Ltd.
Your ONLY knowledge source is the HR Employee Handbook provided below.

RULES:
1. Answer ONLY from the handbook. Do not use outside knowledge.
2. Always cite the section number (e.g. "Section 3.2").
3. If the question cannot be answered from the handbook, say clearly:
   "This is outside the scope of the MediCore HR handbook. Please contact HR directly."
4. Reply in the same language as the question:
   - English question → English answer
   - Bangla question → Bangla answer
5. Be concise but complete. Always state the actual answer, not just the section number.

HANDBOOK:
{handbook}
"""

def ask(question, retries=4):
    prompt = SYSTEM_PROMPT.format(handbook=HANDBOOK) + f"\n\nQuestion: {question}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.1}
    }
    for attempt in range(retries):
        try:
            r = requests.post(API_URL, json=body, timeout=60)
            if r.status_code == 503:
                wait = 15 * (attempt + 1)
                print(f"  503 - waiting {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return parts[0]["text"].strip()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(10)
            else:
                return f"ERROR: {e}"
    return "ERROR: max retries exceeded"

# Read test set
with open(TEST_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

results = []
total = len(rows)
citation_warnings = []

print(f"Running {total} questions...\n")

for i, row in enumerate(rows, 1):
    qid = row["id"]
    q_en = row["question"]
    q_bn = row["question_bn"]

    print(f"[{i}/{total}] {qid} - English...")
    ans_en = ask(q_en)
    time.sleep(3)  # avoid rate limit

    print(f"[{i}/{total}] {qid} - Bangla...")
    ans_bn = ask(q_bn)
    time.sleep(3)

    # Citation spot-check
    bad_en = check_citations(ans_en, HANDBOOK_SECTIONS)
    bad_bn = check_citations(ans_bn, HANDBOOK_SECTIONS)
    if bad_en:
        msg = f"  ⚠️  {qid} EN cites non-existent sections: {bad_en}"
        print(msg)
        citation_warnings.append(msg)
    if bad_bn:
        msg = f"  ⚠️  {qid} BN cites non-existent sections: {bad_bn}"
        print(msg)
        citation_warnings.append(msg)

    results.append({
        "id": qid,
        "question": q_en,
        "question_bn": q_bn,
        "expected": row["expected_answer_summary"],
        "source_section": row["source_section"],
        "must_refuse": row["must_refuse"],
        "answer_en": ans_en,
        "answer_bn": ans_bn,
    })

    print(f"  EN: {ans_en[:80]}...")
    print(f"  BN: {ans_bn[:80]}...")
    print()

# Save raw answers
with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\nDone. Raw answers saved to {OUTPUT_PATH}")

if citation_warnings:
    print(f"\n⚠️  {len(citation_warnings)} citation warning(s) — review manually:")
    for w in citation_warnings:
        print(w)
else:
    print("\n✓ All cited sections exist in the handbook.")
