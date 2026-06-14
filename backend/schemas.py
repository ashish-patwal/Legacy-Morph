from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TargetStack(ApiModel):
    language: str = Field(min_length=1, max_length=80)
    language_version: str | None = Field(default=None, max_length=40)
    framework: str | None = Field(default=None, max_length=80)
    framework_version: str | None = Field(default=None, max_length=40)
    architecture_style: str | None = Field(default=None, max_length=80)
    package_manager: str | None = Field(default=None, max_length=80)
    build_tool: str | None = Field(default=None, max_length=80)
    custom_instructions: str = Field(default="", max_length=4000)


class SourceTechnology(ApiModel):
    language: str = Field(min_length=1, max_length=80)
    framework: str | None = Field(default=None, max_length=120)
    runtime: str | None = Field(default=None, max_length=120)
    version: str | None = Field(default=None, max_length=60)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class RepositoryFile(ApiModel):
    path: str = Field(min_length=1, max_length=1000)
    language: str | None = Field(default=None, max_length=80)
    size_bytes: int = Field(ge=0)
    supported: bool = True
    selected: bool = False
    unsupported_reason: str | None = Field(default=None, max_length=500)


class RepositoryInspectRequest(ApiModel):
    repository_url: HttpUrl
    branch: str | None = Field(default=None, max_length=255)


class RepositoryInspectResponse(ApiModel):
    repository: str
    branch: str
    commit_sha: str | None = None
    files: list[RepositoryFile]
    source_technologies: list[SourceTechnology] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MigrationSessionCreate(ApiModel):
    repository_url: HttpUrl
    branch: str | None = Field(default=None, max_length=255)
    commit_sha: str | None = Field(default=None, max_length=64)
    selected_files: list[str] = Field(min_length=1, max_length=100)
    target: TargetStack


class MigrationSessionResponse(ApiModel):
    id: str
    repository_url: str
    branch: str | None
    commit_sha: str | None
    status: str
    current_step: str
    selected_files: list[str]
    target: TargetStack
    source_technologies: list[SourceTechnology] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FunctionSummary(ApiModel):
    name: str
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    output: str | None = None
    source_path: str | None = None


class AnalyzeRequest(ApiModel):
    migration_session_id: str


class AnalysisResponse(ApiModel):
    migration_session_id: str
    summary: str
    source_technologies: list[SourceTechnology]
    functions: list[FunctionSummary] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    ast_artifact_path: str | None = None
    dependency_schema_path: str | None = None


class MigrateRequest(ApiModel):
    migration_session_id: str


class GeneratedFileResponse(ApiModel):
    id: str
    migration_session_id: str
    source_paths: list[str]
    target_path: str
    content: str
    status: Literal["generated", "needs_changes", "approved", "rejected"]
    review_comments: str | None = None
    created_at: datetime
    updated_at: datetime


class FileReviewRequest(ApiModel):
    decision: Literal["approved", "needs_changes", "rejected"]
    comments: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_comments_for_changes(self) -> FileReviewRequest:
        if self.decision == "needs_changes" and not self.comments:
            raise ValueError("comments are required when requesting changes")
        return self
