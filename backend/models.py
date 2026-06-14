from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class MigrationSession(Base):
    __tablename__ = "migration_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(255))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="created", index=True
    )
    current_step: Mapped[str] = mapped_column(
        String(80), nullable=False, default="repository_inspection"
    )
    source_technologies_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    selected_files_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    target_stack_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    repository_manifest_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    ast_artifact_path: Mapped[str | None] = mapped_column(String(1000))
    dependency_schema_path: Mapped[str | None] = mapped_column(String(1000))
    migration_plan_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    generated_files: Mapped[list[GeneratedFile]] = relationship(
        back_populates="migration_session",
        cascade="all, delete-orphan",
    )


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    migration_session_id: Mapped[str] = mapped_column(
        ForeignKey("migration_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_paths_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    target_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="generated", index=True
    )
    review_comments: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    migration_session: Mapped[MigrationSession] = relationship(
        back_populates="generated_files"
    )
    validation_results: Mapped[list[ValidationResult]] = relationship(
        back_populates="generated_file",
        cascade="all, delete-orphan",
    )


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    generated_file_id: Mapped[str] = mapped_column(
        ForeignKey("generated_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    generated_file: Mapped[GeneratedFile] = relationship(
        back_populates="validation_results"
    )
