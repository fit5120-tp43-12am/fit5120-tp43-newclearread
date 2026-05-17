from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TopLevelStatus = Literal["ok", "partial_error", "error"]
ItemStatus = Literal["ok", "error"]


class TextItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., max_length=128)
    text: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        item_id = value.strip()
        if not item_id:
            raise ValueError("id must not be empty")
        return item_id


class SummaryOptions(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    include_debug: bool = Field(default=False, alias="includeDebug")


class SummaryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    request_id: str | None = Field(default=None, alias="requestId", max_length=128)
    texts: list[TextItem]
    options: SummaryOptions = Field(default_factory=SummaryOptions)


class PublicError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    target: str | None = None


class ItemError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool


class SummaryItemResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    status: ItemStatus
    summary: str
    key_points: list[str] = Field(alias="keyPoints")
    schema_guard_action: str = Field(alias="schemaGuardAction")
    error: ItemError | None = None
    debug: dict[str, Any] | None = None


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    version: str
    model: str


class SummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    request_id: str | None = Field(alias="requestId")
    status: TopLevelStatus
    results: list[SummaryItemResult]
    errors: list[PublicError]
    meta: ResponseMeta


class RuntimeSummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ItemStatus
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    schema_guard_action: str = "none"
    error: ItemError | None = None
    debug: dict[str, Any] | None = None
