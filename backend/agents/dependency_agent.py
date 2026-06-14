from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "1.0"


class DependencyAgent:
    def __init__(self, artifact_root: str | Path = "artifacts") -> None:
        self.artifact_root = Path(artifact_root)

    def generate(
        self,
        migration_session_id: str,
        ast_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        files = ast_artifact.get("files", [])
        symbol_index = _build_symbol_index(files)
        file_index = _build_file_index(files)

        dependencies = []
        unresolved = []
        for file_artifact in files:
            source_file = str(file_artifact.get("source_file", ""))
            dependencies.extend(
                _import_dependencies(source_file, file_artifact, file_index)
            )

            call_dependencies, unresolved_calls = _call_dependencies(
                source_file,
                file_artifact,
                symbol_index,
            )
            dependencies.extend(call_dependencies)
            unresolved.extend(unresolved_calls)

            dependencies.extend(
                _inheritance_dependencies(
                    source_file,
                    file_artifact,
                    symbol_index,
                )
            )

        dependencies = _deduplicate_dependencies(dependencies)
        unresolved = _deduplicate_dependencies(unresolved)
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "migration_session_id": migration_session_id,
            "source_ast_hash": _canonical_hash(ast_artifact),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dependencies": dependencies,
            "unresolved_dependencies": unresolved,
            "frameworks": _framework_summary(files),
            "summary": _summary(files, dependencies, unresolved),
        }
        artifact_path = self._write_artifact(migration_session_id, artifact)
        return {
            "artifact_path": str(artifact_path),
            "artifact_hash": _sha256(artifact_path.read_text(encoding="utf-8")),
            "artifact": artifact,
        }

    def _write_artifact(
        self,
        migration_session_id: str,
        artifact: dict[str, Any],
    ) -> Path:
        directory = self.artifact_root / migration_session_id / "schema"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "dependency-schema.json"
        path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return path


def _build_symbol_index(
    files: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for file_artifact in files:
        source_file = str(file_artifact.get("source_file", ""))
        for symbol in file_artifact.get("symbols", []):
            record = {
                "source_file": source_file,
                "symbol_id": symbol.get("id"),
                "name": symbol.get("name"),
                "kind": symbol.get("kind"),
            }
            name = symbol.get("name")
            if name:
                index[str(name)].append(record)
    return index


def _build_file_index(files: list[dict[str, Any]]) -> dict[str, str]:
    index = {}
    for file_artifact in files:
        path = str(file_artifact.get("source_file", ""))
        if not path:
            continue
        pure_path = PurePosixPath(path)
        index[pure_path.stem] = path
        index[path] = path
        index[path.removesuffix(pure_path.suffix)] = path
    return index


def _import_dependencies(
    source_file: str,
    file_artifact: dict[str, Any],
    file_index: dict[str, str],
) -> list[dict[str, Any]]:
    dependencies = []
    for imported in file_artifact.get("imports", []):
        target_file = _resolve_import_file(str(imported), file_index)
        dependencies.append(
            _dependency(
                source_file=source_file,
                source_symbol=None,
                target=target_file or str(imported),
                dependency_type="file_import" if target_file else "external_import",
                confidence=0.95 if target_file else 0.8,
                evidence={
                    "file": source_file,
                    "import": imported,
                },
                resolved=target_file is not None,
            )
        )
    return dependencies


def _call_dependencies(
    source_file: str,
    file_artifact: dict[str, Any],
    symbol_index: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dependencies = []
    unresolved = []

    for symbol in file_artifact.get("symbols", []):
        source_symbol = str(symbol.get("id") or symbol.get("name") or "")
        for call in symbol.get("calls", []):
            call_name = str(call)
            simple_name = call_name.split(".")[-1]
            candidates = symbol_index.get(simple_name, [])
            target = _select_call_target(source_file, candidates)

            if target:
                dependencies.append(
                    _dependency(
                        source_file=source_file,
                        source_symbol=source_symbol,
                        target=str(target["symbol_id"]),
                        dependency_type="symbol_call",
                        confidence=1.0 if len(candidates) == 1 else 0.7,
                        evidence={
                            "file": source_file,
                            "symbol": source_symbol,
                            "call": call_name,
                        },
                        resolved=True,
                    )
                )
            else:
                unresolved.append(
                    _dependency(
                        source_file=source_file,
                        source_symbol=source_symbol,
                        target=call_name,
                        dependency_type="unresolved_call",
                        confidence=0.5,
                        evidence={
                            "file": source_file,
                            "symbol": source_symbol,
                            "call": call_name,
                        },
                        resolved=False,
                    )
                )

    return dependencies, unresolved


def _inheritance_dependencies(
    source_file: str,
    file_artifact: dict[str, Any],
    symbol_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    dependencies = []
    for symbol in file_artifact.get("symbols", []):
        source_symbol = str(symbol.get("id") or symbol.get("name") or "")
        inherited_types = []
        if symbol.get("extends"):
            inherited_types.append(str(symbol["extends"]))
        inherited_types.extend(str(item) for item in symbol.get("implements", []))

        for inherited_type in inherited_types:
            simple_name = inherited_type.split("<", 1)[0].split(".")[-1].strip()
            candidates = symbol_index.get(simple_name, [])
            target = _select_call_target(source_file, candidates)
            dependencies.append(
                _dependency(
                    source_file=source_file,
                    source_symbol=source_symbol,
                    target=(
                        str(target["symbol_id"])
                        if target
                        else inherited_type
                    ),
                    dependency_type="inheritance",
                    confidence=1.0 if target else 0.8,
                    evidence={
                        "file": source_file,
                        "symbol": source_symbol,
                        "type": inherited_type,
                    },
                    resolved=target is not None,
                )
            )
    return dependencies


def _select_call_target(
    source_file: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not candidates:
        return None
    same_file = [
        candidate
        for candidate in candidates
        if candidate["source_file"] == source_file
    ]
    if len(same_file) == 1:
        return same_file[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _resolve_import_file(
    imported: str,
    file_index: dict[str, str],
) -> str | None:
    normalized = imported.replace("\\", "/")
    candidates = {
        normalized,
        normalized.removeprefix("./"),
        normalized.split("/")[-1],
        normalized.split(".")[-1],
    }
    for candidate in candidates:
        if candidate in file_index:
            return file_index[candidate]
    return None


def _dependency(
    source_file: str,
    source_symbol: str | None,
    target: str,
    dependency_type: str,
    confidence: float,
    evidence: dict[str, Any],
    resolved: bool,
) -> dict[str, Any]:
    return {
        "source_file": source_file,
        "source_symbol": source_symbol,
        "target": target,
        "type": dependency_type,
        "resolved": resolved,
        "required_for_migration": True,
        "confidence": confidence,
        "evidence": evidence,
    }


def _deduplicate_dependencies(
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for dependency in dependencies:
        key = (
            dependency["source_file"],
            dependency.get("source_symbol"),
            dependency["target"],
            dependency["type"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(dependency)
    return sorted(
        unique,
        key=lambda item: (
            item["source_file"],
            item.get("source_symbol") or "",
            item["type"],
            item["target"],
        ),
    )


def _framework_summary(
    files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: dict[str, list[str]] = defaultdict(list)
    for file_artifact in files:
        source_file = str(file_artifact.get("source_file", ""))
        for framework in file_artifact.get("framework_hints", []):
            evidence[str(framework)].append(source_file)

    return [
        {
            "name": framework,
            "evidence": sorted(paths),
        }
        for framework, paths in sorted(evidence.items())
    ]


def _summary(
    files: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    unresolved: list[dict[str, Any]],
) -> dict[str, Any]:
    type_counts = Counter(item["type"] for item in dependencies)
    return {
        "total_files": len(files),
        "dependency_count": len(dependencies),
        "unresolved_count": len(unresolved),
        "dependency_types": dict(sorted(type_counts.items())),
        "files_with_dependencies": len(
            {item["source_file"] for item in dependencies}
        ),
    }


def _canonical_hash(value: dict[str, Any]) -> str:
    return _sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
