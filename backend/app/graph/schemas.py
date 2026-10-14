from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

SubQuestion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]


class Plan(BaseModel):
    subquestions: list[SubQuestion] = Field(min_length=1, max_length=4)


class Claim(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=600)]
    source_ids: list[
        Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^S\d+$")]
    ] = Field(min_length=1, max_length=4)


class Answer(BaseModel):
    claims: list[Claim] = Field(max_length=8)  # empty list = "cannot answer from these sources"
    limitations: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""