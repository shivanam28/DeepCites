import re

STOPWORDS = {
    "the", "and", "for", "are", "with", "that", "this", "from", "have", "has", "not",
    "but", "can", "may", "its", "also", "than", "more", "some", "into", "such", "been",
    "their", "which", "while", "these", "those", "other", "most", "many", "over",
    "between", "among", "about", "does", "did", "was", "were", "will", "would", "could",
    "should", "however", "including", "often", "less", "only",
}
WORD_RE = re.compile(r"[a-z0-9]+")
NUM_RE = re.compile(r"\d+(?:\.\d+)?")

WEAK_BELOW = 0.30  # starting guess; we'll calibrate it against real output


def _stem(word: str) -> str:
    """Very crude: drop one trailing 's', keep the first 6 characters."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word[:6]


def _terms(text: str, exclude: frozenset = frozenset()) -> set[str]:
    out = set()
    for w in WORD_RE.findall(text.lower()):
        if len(w) < 3 or w in STOPWORDS or w.isdigit():
            continue
        stem = _stem(w)
        if stem not in exclude:
            out.add(stem)
    return out


def check_claim(claim: dict, question: str, evidence_by_id: dict) -> dict:
    cited_text = " ".join(
        evidence_by_id[s]["title"] + " " + evidence_by_id[s]["snippet"]
        for s in claim["source_ids"]
    )
    topic_terms = frozenset(_terms(question))  # words every snippet shares; don't count them
    claim_terms = _terms(claim["text"], exclude=topic_terms)
    source_terms = _terms(cited_text)
    overlap = len(claim_terms & source_terms) / len(claim_terms) if claim_terms else 0.0

    missing_numbers = sorted(set(NUM_RE.findall(claim["text"])) - set(NUM_RE.findall(cited_text)))
    if missing_numbers:
        verdict = "unsupported"
    elif overlap < WEAK_BELOW:
        verdict = "weak"
    else:
        verdict = "ok"
    return {"overlap": round(overlap, 2), "missing_numbers": missing_numbers, "verdict": verdict}