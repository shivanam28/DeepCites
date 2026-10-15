def render_answer(claims: list[dict], limitations: str, evidence: list[dict]) -> str:
    by_id = {e["source_id"]: e for e in evidence}
    paragraphs, cited = [], []
    for c in claims:
        marks = "".join(f"[{s}]" for s in c["source_ids"])
        note = " [weak support]" if c.get("flag") == "weak" else ""
        paragraphs.append(f"{c['text']} {marks}{note}")
        for s in c["source_ids"]:
            if s not in cited:
                cited.append(s)
    cited.sort(key=lambda s: int(s[1:]))

    out = "\n\n".join(paragraphs)
    if limitations:
        out += f"\n\nLimitations: {limitations}"
    out += "\n\nSources:\n" + "\n".join(
        f"[{s}] {by_id[s]['title']} - {by_id[s]['url']}" for s in cited
    )
    return out