# HR Policy Assistant

A bilingual (English / Bangla) conversational AI assistant that answers employee questions about company HR policies — grounded strictly in a provided handbook, with no hallucination outside it.

**Live demo:** https://medicore-hr-assistant.streamlit.app

---

## What it does

- Answers HR policy questions in **English or Bangla** based on language of the question
- Cites the exact **section number** for every answer
- **Refuses to answer** questions not covered by the handbook (e.g. salary of a manager, competitor policies)
- Runs entirely on the **Gemini free tier** — zero cost

---

## Accuracy Results

Evaluated against a 50-question blind test set (40 answerable + 10 must-refuse traps).

| Metric | Target | Result |
|---|---|---|
| English accuracy | ≥ 90% | **92.5%** |
| Bangla accuracy | ≥ 90% | **92.5%** |
| EN vs BN gap | ≤ 5 percentage points | **0 pp** |
| Refusal rate (out-of-scope) | 10 / 10 | **10 / 10** |

All four targets met on first evaluation run.

---

## Tech Stack

| Component | Choice |
|---|---|
| LLM | Gemini (`gemini-3.5-flash-lite`) via REST API |
| UI | Streamlit |
| Language | Python 3.11 |
| Deployment | Streamlit Cloud |
| Cost | Gemini free tier (subject to quota limits) |

---

## How it works

1. The full HR handbook is loaded as context on every request
2. A strict system prompt instructs the model to answer only from the handbook, cite sections, refuse out-of-scope questions, and reply in the user's language
3. The model returns a complete response via the Gemini REST API, displayed in the Streamlit chat interface

---

## Run locally

```bash
git clone https://github.com/tarifhassan27/hr-policy-assistant.git
cd hr-policy-assistant
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

Create a `.env` file:
```
GEMINI_API_KEY=your_key_here
```

Run:
```bash
streamlit run app.py
```

---

## Project structure

```
hr-policy-assistant/
├── app.py               # Streamlit chatbot
├── scorer.py            # Generates model answers for all 50 test questions
├── evaluate.py          # Scores raw answers; outputs evaluation_report.txt
├── handbook/
│   └── handbook.md      # HR policy handbook (source of truth)
├── tests/
│   └── test_set.csv     # 50-question blind test set
├── results/
│   ├── raw_answers.csv        # Model outputs for all 50 questions
│   └── evaluation_report.txt  # Scored accuracy results
├── definitions.md       # Locked accuracy targets (set before any code)
└── requirements.txt
```
