import operator
from typing import Annotated, TypedDict


class Evidence(TypedDict):
    source_id: str
    title: str
    url: str
    snippet: str


class ResearchState(TypedDict, total=False):
    question: str
    subquestions: list[str]
    evidence: Annotated[list[Evidence], operator.add]
    iteration: int
    answer: str
    trace: Annotated[list[str], operator.add]
    claims: list[dict]
    citation_problems: list[str]
    limitations: str
    claim_checks: list[dict]