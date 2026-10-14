from app.graph.schemas import Claim


def validate_claims(claims: list[Claim], evidence: list[dict]) -> tuple[list[Claim], list[str]]:
    """Keep only claims whose every cited source ID exists in the evidence."""
    known = {e["source_id"] for e in evidence}
    valid, problems = [], []
    for i, claim in enumerate(claims, start=1):
        unknown = [s for s in claim.source_ids if s not in known]
        if unknown:
            problems.append(f"claim {i} cites unknown source(s): {', '.join(unknown)}")
        else:
            valid.append(claim)
    return valid, problems