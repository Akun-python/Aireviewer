from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


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
    data: Dict = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    mode: str
    title: str
    status: str
    input_filename: str
    params: Dict = Field(default_factory=dict)
    created_at: str
    updated_at: str
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    run_dir: str
    result: Dict = Field(default_factory=dict)
    artifacts: List[ArtifactResponse] = Field(default_factory=list)
    event_count: int = 0
    events: List[RunEventResponse] = Field(default_factory=list)
    conversation_id: str = ""
    version_no: Optional[int] = None
    base_run_id: str = ""
    source_artifact: str = ""


class RunListResponse(BaseModel):
    runs: List[RunResponse]


class HealthResponse(BaseModel):
    status: str


class ReviewConversationMessageResponse(BaseModel):
    id: str
    role: str
    mode: str
    content: str
    status: str
    base_source: str = ""
    base_run_id: str = ""
    linked_run_id: str = ""
    metadata: Dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ReviewConversationVersionResponse(BaseModel):
    version_no: int
    run_id: str
    base_run_id: str = ""
    artifact_name: str
    source_artifact: str = ""
    label: str
    diagnostics_run_id: str
    download_url: str
    created_at: str


class ReviewConversationListItemResponse(BaseModel):
    id: str
    title: str
    input_filename: str
    preset_key: str
    created_at: str
    updated_at: str
    head_run_id: str = ""
    head_version_no: int = 0
    active_run_id: str = ""
    message_count: int = 0
    version_count: int = 0
    last_message_excerpt: str = ""


class ReviewConversationResponse(BaseModel):
    id: str
    title: str
    input_filename: str
    preset_key: str
    defaults: Dict = Field(default_factory=dict)
    created_at: str
    updated_at: str
    head_run_id: str = ""
    head_version_no: int = 0
    active_run_id: str = ""
    original_artifact: ArtifactResponse
    messages: List[ReviewConversationMessageResponse] = Field(default_factory=list)
    versions: List[ReviewConversationVersionResponse] = Field(default_factory=list)
    head_run: Optional[RunResponse] = None


class ReviewConversationListResponse(BaseModel):
    conversations: List[ReviewConversationListItemResponse]


class ReviewConversationMessageRequest(BaseModel):
    mode: str
    content: str
    base_source: str = "latest"
    base_run_id: str = ""
    options_patch: Dict = Field(default_factory=dict)


class ReviewConversationMessageActionResponse(BaseModel):
    user_message: ReviewConversationMessageResponse
    assistant_message: ReviewConversationMessageResponse
    linked_run: Optional[RunResponse] = None
