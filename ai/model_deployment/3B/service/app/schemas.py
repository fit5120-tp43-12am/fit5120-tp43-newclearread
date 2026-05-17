from pydantic import BaseModel, Field, field_validator


class TextBlock(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    text: str

    @field_validator("id")
    @classmethod
    def clean_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("id must not be empty")
        return cleaned


class SummaryOptions(BaseModel):
    includeDebug: bool = False


class SummaryRequest(BaseModel):
    requestId: str | None = Field(default=None, max_length=200)
    texts: list[TextBlock]
    options: SummaryOptions = Field(default_factory=SummaryOptions)


class ItemError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class SummaryResult(BaseModel):
    id: str
    status: str
    summary: str = ""
    keyPoints: list[str] = Field(default_factory=list)
    schemaGuardAction: str = "none"
    error: ItemError | None = None


class SummaryMeta(BaseModel):
    service: str
    version: str
    model: str
    modelBackend: str = "vllm"


class SummaryResponse(BaseModel):
    requestId: str | None = None
    status: str
    results: list[SummaryResult]
    errors: list[ItemError] = Field(default_factory=list)
    meta: SummaryMeta
