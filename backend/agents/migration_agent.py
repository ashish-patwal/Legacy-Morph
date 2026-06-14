from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ai_service import AIService


SCHEMA_VERSION = "1.0"


class MigrationAgentError(RuntimeError):
    pass


class MigrationAgent:
    def __init__(
        self,
        ai_service: AIService,
        artifact_root: str | Path = "artifacts",
    ) -> None:
        self.ai_service = ai_service
        self.artifact_root = Path(artifact_root)

    async def analyze(
        self,
        migration_session_id: str,
        repository_manifest: dict[str, Any],
        ast_artifact: dict[str, Any],
        dependency_schema: dict[str, Any],
    ) -> dict[str, Any]:
        analysis = await self.ai_service.analyze_code(
            repository_manifest,
            ast_artifact,
            dependency_schema,
        )
        normalized = _normalize_analysis(analysis)
        path = self._write_json(
            migration_session_id,
            "analysis",
            "analysis.json",
            {
                "schema_version": SCHEMA_VERSION,
                "migration_session_id": migration_session_id,
                "created_at": _utc_timestamp(),
                "analysis": normalized,
            },
        )
        return {
            "artifact_path": str(path),
            "artifact_hash": _file_hash(path),
            "analysis": normalized,
        }

    async def create_plan(
        self,
        migration_session_id: str,
        analysis: dict[str, Any],
        ast_artifact: dict[str, Any],
        dependency_schema: dict[str, Any],
        target_stack: dict[str, Any],
    ) -> dict[str, Any]:
        raw_plan = await self.ai_service.create_migration_plan(
            analysis,
            ast_artifact,
            dependency_schema,
            target_stack,
        )
        plan = _normalize_plan(raw_plan, target_stack)
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "migration_session_id": migration_session_id,
            "created_at": _utc_timestamp(),
            "source_ast_hash": _canonical_hash(ast_artifact),
            "dependency_schema_hash": _canonical_hash(dependency_schema),
            "target_stack": target_stack,
            "status": "awaiting_approval",
            "plan": plan,
        }
        path = self._write_json(
            migration_session_id,
            "plan",
            "migration-plan.json",
            artifact,
        )
        return {
            "artifact_path": str(path),
            "artifact_hash": _file_hash(path),
            "artifact": artifact,
        }

    async def generate_next_file(
        self,
        migration_session_id: str,
        plan_artifact: dict[str, Any],
        source_documents: list[dict[str, Any]],
        ast_artifact: dict[str, Any],
        dependency_schema: dict[str, Any],
        approved_files: list[dict[str, Any]],
        review_comments: str | None = None,
    ) -> dict[str, Any]:
        if plan_artifact.get("status") != "approved":
            raise MigrationAgentError(
                "Migration plan must be approved before generating files."
            )

        plan = plan_artifact.get("plan", {})
        target_stack = plan_artifact.get("target_stack", {})
        file_plan = _next_file_plan(plan, approved_files)
        if file_plan is None:
            raise MigrationAgentError("All planned files are already approved.")

        source_paths = set(file_plan.get("source_paths", []))
        source_slices = [
            document
            for document in source_documents
            if document.get("path") in source_paths
        ]
        relevant_ast = _relevant_ast(ast_artifact, source_paths)
        relevant_dependencies = _relevant_dependencies(
            dependency_schema,
            source_paths,
        )

        generated = await self.ai_service.generate_file(
            target_stack=target_stack,
            file_plan=file_plan,
            source_slices=source_slices,
            relevant_ast=relevant_ast,
            relevant_dependencies=relevant_dependencies,
            approved_files=approved_files,
            review_comments=review_comments,
        )
        normalized = _normalize_generated_file(generated, file_plan)
        path = self._write_json(
            migration_session_id,
            "generated",
            _artifact_filename(normalized["target_path"]),
            {
                "schema_version": SCHEMA_VERSION,
                "migration_session_id": migration_session_id,
                "created_at": _utc_timestamp(),
                "file_plan": file_plan,
                "generated_file": normalized,
            },
        )
        return {
            "artifact_path": str(path),
            "artifact_hash": _file_hash(path),
            "file_plan": file_plan,
            "generated_file": normalized,
        }

    def approve_plan(
        self,
        plan_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        approved = dict(plan_artifact)
        approved["status"] = "approved"
        approved["approved_at"] = _utc_timestamp()
        return approved

    def _write_json(
        self,
        migration_session_id: str,
        category: str,
        filename: str,
        value: dict[str, Any],
    ) -> Path:
        directory = self.artifact_root / migration_session_id / category
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return path


def _normalize_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(analysis.get("summary", "")).strip(),
        "source_technologies": _list_of_dicts(
            analysis.get("source_technologies")
        ),
        "functions": _list_of_dicts(analysis.get("functions")),
        "business_rules": _string_list(analysis.get("business_rules")),
        "repeated_patterns": _string_list(analysis.get("repeated_patterns")),
        "risks": _string_list(analysis.get("risks")),
        "unknowns": _string_list(analysis.get("unknowns")),
    }


def _normalize_plan(
    raw_plan: dict[str, Any],
    target_stack: dict[str, Any],
) -> dict[str, Any]:
    raw_files = raw_plan.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise MigrationAgentError("Migration plan must contain at least one file.")

    files = []
    seen_paths = set()
    for index, raw_file in enumerate(raw_files, start=1):
        if not isinstance(raw_file, dict):
            raise MigrationAgentError("Every planned file must be an object.")

        target_path = _safe_target_path(str(raw_file.get("target_path", "")))
        if target_path in seen_paths:
            raise MigrationAgentError(
                f"Duplicate target path in migration plan: {target_path}"
            )
        seen_paths.add(target_path)
        files.append(
            {
                "order": index,
                "target_path": target_path,
                "source_paths": _string_list(raw_file.get("source_paths")),
                "purpose": str(raw_file.get("purpose", "")).strip(),
                "depends_on": _string_list(raw_file.get("depends_on")),
                "symbols_to_migrate": _string_list(
                    raw_file.get("symbols_to_migrate")
                ),
                "acceptance_criteria": _string_list(
                    raw_file.get("acceptance_criteria")
                ),
            }
        )

    _validate_plan_dependencies(files)
    return {
        "target_summary": str(
            raw_plan.get("target_summary")
            or _target_summary(target_stack)
        ).strip(),
        "support_level": _support_level(raw_plan.get("support_level")),
        "architecture_notes": _string_list(
            raw_plan.get("architecture_notes")
        ),
        "files": files,
        "unresolved_questions": _string_list(
            raw_plan.get("unresolved_questions")
        ),
        "risks": _string_list(raw_plan.get("risks")),
    }


def _normalize_generated_file(
    generated: dict[str, Any],
    file_plan: dict[str, Any],
) -> dict[str, Any]:
    expected_path = file_plan["target_path"]
    returned_path = _safe_target_path(
        str(generated.get("target_path") or expected_path)
    )
    if returned_path != expected_path:
        raise MigrationAgentError(
            "Generated target path does not match the approved plan."
        )

    content = generated.get("content")
    if not isinstance(content, str) or not content.strip():
        raise MigrationAgentError("Generated file content cannot be empty.")

    source_paths = _string_list(generated.get("source_paths"))
    planned_source_paths = set(file_plan.get("source_paths", []))
    if not set(source_paths).issubset(planned_source_paths):
        raise MigrationAgentError(
            "Generated file referenced source paths outside the approved plan."
        )

    return {
        "target_path": expected_path,
        "content": content,
        "source_paths": source_paths,
        "source_to_target_map": _list_of_dicts(
            generated.get("source_to_target_map")
        ),
        "assumptions": _string_list(generated.get("assumptions")),
        "unresolved_dependencies": _string_list(
            generated.get("unresolved_dependencies")
        ),
    }


def _next_file_plan(
    plan: dict[str, Any],
    approved_files: list[dict[str, Any]],
) -> dict[str, Any] | None:
    approved_paths = {
        str(file.get("target_path"))
        for file in approved_files
        if file.get("status") == "approved"
    }
    for file_plan in plan.get("files", []):
        if file_plan["target_path"] not in approved_paths:
            missing_dependencies = set(file_plan.get("depends_on", [])) - approved_paths
            if missing_dependencies:
                continue
            return file_plan
    return None


def _relevant_ast(
    ast_artifact: dict[str, Any],
    source_paths: set[str],
) -> dict[str, Any]:
    return {
        "schema_version": ast_artifact.get("schema_version"),
        "files": [
            file_artifact
            for file_artifact in ast_artifact.get("files", [])
            if file_artifact.get("source_file") in source_paths
        ],
    }


def _relevant_dependencies(
    dependency_schema: dict[str, Any],
    source_paths: set[str],
) -> dict[str, Any]:
    return {
        "schema_version": dependency_schema.get("schema_version"),
        "dependencies": [
            dependency
            for dependency in dependency_schema.get("dependencies", [])
            if dependency.get("source_file") in source_paths
            or dependency.get("target") in source_paths
        ],
        "unresolved_dependencies": [
            dependency
            for dependency in dependency_schema.get(
                "unresolved_dependencies",
                [],
            )
            if dependency.get("source_file") in source_paths
        ],
    }


def _validate_plan_dependencies(files: list[dict[str, Any]]) -> None:
    order_by_path = {
        file_plan["target_path"]: file_plan["order"]
        for file_plan in files
    }
    for file_plan in files:
        for dependency in file_plan["depends_on"]:
            if dependency not in order_by_path:
                raise MigrationAgentError(
                    f"Planned dependency does not exist: {dependency}"
                )
            if order_by_path[dependency] >= file_plan["order"]:
                raise MigrationAgentError(
                    "Planned dependencies must appear before their consumers."
                )


def _safe_target_path(value: str) -> str:
    path = PurePosixPath(value.strip())
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        raise MigrationAgentError(f"Unsafe target path: {value}")
    return path.as_posix()


def _artifact_filename(target_path: str) -> str:
    safe_name = target_path.replace("/", "__").replace("\\", "__")
    return f"{safe_name}.json"


def _target_summary(target_stack: dict[str, Any]) -> str:
    language = str(target_stack.get("language", "Unknown target"))
    framework = target_stack.get("framework")
    return f"{language} with {framework}" if framework else language


def _support_level(value: Any) -> str:
    normalized = str(value or "experimental").lower()
    return normalized if normalized in {"supported", "experimental"} else "experimental"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _canonical_hash(value: dict[str, Any]) -> str:
    return _sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )


def _file_hash(path: Path) -> str:
    return _sha256(path.read_text(encoding="utf-8"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
