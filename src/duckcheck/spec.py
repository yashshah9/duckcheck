"""Check specification models."""

from pydantic import BaseModel, Field


class CheckSpec(BaseModel):
    name: str
    type: str
    table: str
    column: str | None = None
    values: list[str] = Field(default_factory=list)


class SuiteSpec(BaseModel):
    name: str
    source: str
    checks: list[CheckSpec] = Field(default_factory=list)
