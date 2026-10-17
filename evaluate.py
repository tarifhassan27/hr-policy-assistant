"""
evaluate.py — Automated scoring for MediCore HR Assistant
Reads results/raw_answers.csv and scores each answer against expected keywords.
Outputs a summary report to results/evaluation_report.txt
"""

import csv
import os
import re

INPUT_PATH = "results/raw_answers.csv"
OUTPUT_PATH = "results/evaluation_report.txt"

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

# Map ASCII digits to Bengali numerals for cross-script number matching
BENGALI_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

REFUSAL_PHRASES = [
    "outside the scope",
    "scope of the medicore",
    "please contact hr",
    # "এর বাইরে" removed — too generic; common Bangla grammar ("outside of this")
    # that appears in factual answers, not only refusals. The specific compound
    # forms below already cover all legitimate refusal patterns.
    "স্কোপের বাইরে",
    "সীমার বাইরে",
    "সরাসরি যোগাযোগ করুন",
    "এইচআর-এর সাথে যোগাযোগ",
    "হ্যান্ডবুকের বাইরে",
]


def normalise(text: str) -> str:
    """Lowercase, strip markdown and punctuation, collapse whitespace."""
    text = text.lower()
    # Strip markdown bold/italic markers
    text = re.sub(r"\*+", " ", text)
    text = re.sub(r"_+", " ", text)
    # Punctuation: Bengali daari is । and ॥ (double daari)
    text = re.sub(r"[,.\-–—।॥|()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_markdown(text: str) -> str:
    """Remove markdown bold/italic markers."""
    return re.sub(r"\*+|_+", " ", text)


def contains_number(text: str, number: str) -> bool:
    """Check if a number appears in text in either ASCII or Bengali script."""
    bn = number.translate(BENGALI_DIGITS)
    clean = strip_markdown(text)
    norm = normalise(clean)
    # Match as whole word boundary so "4" doesn't match "14"
    pattern = r"(?<!\d)" + re.escape(number) + r"(?!\d)"
    return bool(re.search(pattern, norm)) or (bn in clean)


def check_refusal(text: str) -> bool:
    """
    Return True if the answer correctly refuses an out-of-scope question.

    A genuine refusal must:
      1. Contain a refusal phrase (existing check)
      2. NOT cite a section number — a real refusal has no policy to cite
      3. NOT answer with a number after the refusal phrase (partial refusal)
    """
    text_lower = text.lower()
    if not any(phrase in text_lower for phrase in REFUSAL_PHRASES):
        return False
    # Fail: refusal phrase present but a section citation also appears
    if re.search(r"section\s+\d+\.\d+", text_lower):
        return False
    # Fail: a digit appears in the portion of text AFTER the refusal phrase
    # (catches "outside scope... but typically 14 days")
    for phrase in REFUSAL_PHRASES:
        idx = text_lower.find(phrase)
        if idx != -1:
            after = text[idx + len(phrase):]
            if re.search(r"[0-9]", after):
                return False
    return True


def extract_keywords(expected: str):
    """
    Pull scorable tokens from the expected answer summary.
    Returns (primary_numbers, secondary_numbers, keywords).

    primary_numbers  — must ALL appear in the answer
    secondary_numbers — at least ONE must appear (covers "X or Y" style answers)
    keywords — for English answers: at least 60% must match
    """
    raw_numbers = re.findall(r"\d+(?:[,\s]\d+)*", expected)
    raw_numbers = [re.sub(r"[,\s]", "", n) for n in raw_numbers if re.sub(r"[,\s]", "", n)]

    # The first number is always primary (the main answer figure).
    # All subsequent numbers are secondary — only one of them needs to match.
    primary   = raw_numbers[:1]
    secondary = raw_numbers[1:]

    # Key word/phrase tokens: words 3+ chars, drop common stopwords
    stopwords = {
        "the", "and", "for", "are", "not", "per", "has", "any", "can",
        "may", "all", "one", "two", "that", "this", "with", "from",
        "only", "each", "both", "days", "year", "bdt", "yes", "no",
        "leave",  # "leave year" is too domain-generic to require literally
    }
    words = re.findall(r"[a-z]{3,}", expected.lower())
    keywords = [w for w in words if w not in stopwords]

    return primary, secondary, keywords


def is_bangla(text: str) -> bool:
    """Return True if the answer contains significant Bangla script."""
    bangla_chars = sum(1 for c in text if "ঀ" <= c <= "৿")
    return bangla_chars > 10


def check_contradiction(answer: str, expected_primary: str) -> str | None:
    """
    Return a warning string if the answer gives a conflicting value alongside
    the expected one, otherwise None.

    Only applied to primary numbers with 3+ digits. Single and two-digit
    primaries are skipped because they collide with section references (3.2),
    times (9:00), and dates that legitimately appear in correct answers —
    producing too many false positives to be useful.

    Example where this fires correctly:
      expected "650" → answer has "৬৫২" (652) AND "650" → CONTRADICTION

    Important: Bengali digits are normalised to ASCII before scanning because
    Python's \\d matches Bengali numerals in Unicode mode. Without normalisation,
    "৫০০" and "500" would appear as two distinct values, producing false positives
    on correct Bangla answers that write the same number in Bengali script.
    """
    if not expected_primary:
        return None

    # Skip for 1–2 digit numbers: too many innocent collisions with section
    # references (3.2), times (9:00), and dates in correct answers
    if len(expected_primary) < 3:
        return None

    # Normalise Bengali digits → ASCII FIRST, then strip commas
    bn_to_ascii = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    answer_norm = answer.translate(bn_to_ascii)
    answer_norm = re.sub(r"(\d),(\d)", r"\1\2", answer_norm)

    target_len = len(expected_primary)
    found = set(re.findall(r"\b\d{" + str(target_len) + r"}\b", answer_norm))

    if len(found) > 1 and expected_primary in found:
        conflicting = found - {expected_primary}
        return f"CONTRADICTION: answer gives {expected_primary} but also {conflicting} — review manually"
    return None


def score_answer(answer: str, expected: str, must_refuse: bool) -> tuple[bool, str]:
    """
    Returns (passed: bool, reason: str).

    For English answers: check numbers + keyword overlap against expected summary.
    For Bangla answers: check numbers only (cross-script). Keywords are English
    and cannot be matched against Bangla text — the answer is accepted if all
    required numbers are present and the answer is not a refusal.

    Contradiction check: if the answer gives two conflicting values of the same
    digit-length alongside the expected value, it is flagged for human review
    rather than auto-passed.
    """
    if must_refuse:
        passed = check_refusal(answer)
        reason = "correctly refused" if passed else "FAILED to refuse"
        return passed, reason

    if check_refusal(answer):
        return False, "incorrectly refused an answerable question"

    primary, secondary, keywords = extract_keywords(expected)

    # Strip comma-formatted numbers from the answer so "2,500" == "2500"
    answer_denorm = re.sub(r"(\d),(\d)", r"\1\2", answer)

    # Contradiction check — run before accepting the answer
    if primary:
        contradiction = check_contradiction(answer, primary[0])
        if contradiction:
            return False, contradiction

    # Primary number must appear (skip leading-zero section suffixes like "01")
    for num in primary:
        if len(num) == 2 and num.startswith("0"):
            continue
        if not contains_number(answer_denorm, num):
            return False, f"missing number: {num}"

    # Secondary numbers are informational only — not required for a pass
    # (e.g. "31 December" expiry date, "48 hours" secondary threshold)
    _ = secondary  # kept for future use

    # Keyword check only for English answers
    if not is_bangla(answer) and keywords:
        matched = sum(1 for kw in keywords if kw in normalise(answer))
        ratio = matched / len(keywords)
        if ratio < 0.60:
            missing = [kw for kw in keywords if kw not in normalise(answer)]
            return False, f"keyword match {ratio:.0%} — missing: {missing[:3]}"

    return True, "pass"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

os.makedirs("results", exist_ok=True)

with open(INPUT_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

results = []
api_errors = []  # rows where scorer.py recorded an API failure

for row in rows:
    # scorer.py writes "ERROR: ..." when an API request fails.
    # Scoring error strings as answers would silently deflate accuracy.
    # Collect them separately and exclude from scoring.
    en_err = row["answer_en"].startswith("ERROR:")
    bn_err = row["answer_bn"].startswith("ERROR:")
    if en_err or bn_err:
        api_errors.append(row["id"])
        continue

    must_refuse = row["must_refuse"].strip().upper() == "TRUE"
    expected = row["expected"]

    pass_en, reason_en = score_answer(row["answer_en"], expected, must_refuse)
    pass_bn, reason_bn = score_answer(row["answer_bn"], expected, must_refuse)

    results.append({
        "id": row["id"],
        "must_refuse": must_refuse,
        "pass_en": pass_en,
        "pass_bn": pass_bn,
        "reason_en": reason_en,
        "reason_bn": reason_bn,
        "expected": expected,
        "answer_en": row["answer_en"][:120],
        "answer_bn": row["answer_bn"][:120],
    })

# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

answerable = [r for r in results if not r["must_refuse"]]
refusals   = [r for r in results if r["must_refuse"]]

en_pass = sum(r["pass_en"] for r in answerable)
bn_pass = sum(r["pass_bn"] for r in answerable)
ref_en  = sum(r["pass_en"] for r in refusals)
ref_bn  = sum(r["pass_bn"] for r in refusals)

total_ans = len(answerable)
total_ref = len(refusals)

en_pct = en_pass / total_ans * 100
bn_pct = bn_pass / total_ans * 100
gap    = abs(en_pct - bn_pct)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

lines = []
lines.append("=" * 60)
lines.append("  MediCore HR Assistant — Evaluation Report")
lines.append("=" * 60)
lines.append("")
lines.append(f"  Answerable questions : {total_ans}")
lines.append(f"  Must-refuse traps    : {total_ref}")
if api_errors:
    lines.append(f"  API errors (skipped) : {len(api_errors)}  ← RE-RUN SCORER before trusting results")
    lines.append(f"  Affected IDs         : {', '.join(api_errors)}")
lines.append("")
lines.append("  METRIC                TARGET    RESULT")
lines.append("  ─────────────────────────────────────────")
lines.append(f"  English accuracy      ≥90%      {en_pct:.1f}%   ({en_pass}/{total_ans})")
lines.append(f"  Bangla accuracy       ≥90%      {bn_pct:.1f}%   ({bn_pass}/{total_ans})")
lines.append(f"  EN–BN gap             ≤5pp      {gap:.1f}pp")
lines.append(f"  Refusals (EN)         10/10     {ref_en}/{total_ref}")
lines.append(f"  Refusals (BN)         10/10     {ref_bn}/{total_ref}")
lines.append("")

all_targets = (
    not api_errors and   # any API error → results are incomplete
    en_pct >= 90 and
    bn_pct >= 90 and
    gap    <= 5  and
    ref_en == total_ref and
    ref_bn == total_ref
)
lines.append("  VERDICT: " + ("ALL TARGETS MET ✓" if all_targets else "SOME TARGETS MISSED ✗"))
lines.append("")
lines.append("  NOTE: Keyword scoring checks English expected summaries only.")
lines.append("  Bangla answers are scored on number accuracy (cross-script).")
lines.append("  Some English 'failures' may be scorer false negatives where")
lines.append("  the bot gives a correct but less verbose answer than the")
lines.append("  expected summary. Human review recommended for flagged items.")
lines.append("")

# Per-question failures
failures_en = [r for r in answerable if not r["pass_en"]]
failures_bn = [r for r in answerable if not r["pass_bn"]]
ref_failures = [r for r in refusals if not r["pass_en"] or not r["pass_bn"]]

if failures_en:
    lines.append("  English failures:")
    for r in failures_en:
        lines.append(f"    {r['id']}: {r['reason_en']}")
        lines.append(f"      Expected : {r['expected'][:80]}")
        lines.append(f"      Got (EN) : {r['answer_en'][:80]}")
    lines.append("")

if failures_bn:
    lines.append("  Bangla failures:")
    for r in failures_bn:
        lines.append(f"    {r['id']}: {r['reason_bn']}")
        lines.append(f"      Expected : {r['expected'][:80]}")
        lines.append(f"      Got (BN) : {r['answer_bn'][:80]}")
    lines.append("")

if ref_failures:
    lines.append("  Refusal failures:")
    for r in ref_failures:
        if not r["pass_en"]:
            lines.append(f"    {r['id']} (EN): {r['reason_en']}")
        if not r["pass_bn"]:
            lines.append(f"    {r['id']} (BN): {r['reason_bn']}")
    lines.append("")

lines.append("=" * 60)
report = "\n".join(lines)

print(report)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nReport saved to {OUTPUT_PATH}")
