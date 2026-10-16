"""
patch_q033_q034.py — Re-run Q033 and Q034 and update raw_answers.csv in place.
Run this when those rows contain ERROR due to a network drop during scorer.py.
"""

import csv
import requests
import os
import time

with open(".env") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY"):
            API_KEY = line.strip().split("=", 1)[1]

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={API_KEY}"
HANDBOOK_PATH = "handbook/handbook.md"
OUTPUT_PATH = "results/raw_answers.csv"

with open(HANDBOOK_PATH, encoding="utf-8") as f:
    HANDBOOK = f.read()

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

PATCH_IDS = {"Q033", "Q034"}

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

# Read existing CSV
with open(OUTPUT_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

fieldnames = list(rows[0].keys())

# Patch the two rows
for row in rows:
    if row["id"] in PATCH_IDS:
        print(f"Re-running {row['id']} - English...")
        row["answer_en"] = ask(row["question"])
        time.sleep(3)
        print(f"Re-running {row['id']} - Bangla...")
        row["answer_bn"] = ask(row["question_bn"])
        time.sleep(3)
        print(f"  EN: {row['answer_en'][:80]}")
        print(f"  BN: {row['answer_bn'][:80]}")
        print()

# Write back
with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Done. Patched Q033 and Q034 in {OUTPUT_PATH}")
print("Now run: venv\\Scripts\\python.exe evaluate.py")
