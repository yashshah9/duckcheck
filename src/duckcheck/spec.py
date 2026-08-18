"""Check specification models."""

from pydantic import BaseModel, Field


class CheckSpec(BaseModel):
    name: str
    type: str
    table: str = "source_data"
    column: str | None = None
    values: list[str] = Field(default_factory=list)
    sql: str | None = None
    max_age: str | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    tolerance_pct: float | None = None


class SuiteSpec(BaseModel):
    name: str
    source: str
    source_table: str | None = None
    baseline: str | None = None
    checks: list[CheckSpec] = Field(default_factory=list)
