from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    name: str
    label: str
    path: str
    filename: str
    size_bytes: int
    content_type: str
    download_url: str


class RunEventResponse(BaseModel):
    id: int
    ts: str
    type: str
    message: str = ""
    data: dict = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    mode: str
    title: str
    status: str
    input_filename: str
    params: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    run_dir: str
    result: dict = Field(default_factory=dict)
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    event_count: int = 0
    events: list[RunEventResponse] = Field(default_factory=list)


class RunListResponse(BaseModel):
    runs: list[RunResponse]


class HealthResponse(BaseModel):
    status: str

