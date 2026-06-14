from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SourceDocument:
    path: str
    language: str
    content: str


class ParserAdapter(Protocol):
    languages: frozenset[str]

    def parse(self, document: SourceDocument) -> dict[str, Any]: ...


class JavaScriptParserAdapter:
    languages = frozenset({"JavaScript", "TypeScript"})

    _function_patterns = (
        re.compile(
            r"(?P<prefix>\b(?:export\s+)?(?:async\s+)?function\s+)"
            r"(?P<name>[A-Za-z_$][\w$]*)\s*"
            r"\((?P<params>[^)]*)\)\s*\{"
        ),
        re.compile(
            r"(?P<prefix>\b(?:const|let|var)\s+)"
            r"(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
            r"(?:async\s+)?\((?P<params>[^)]*)\)\s*=>\s*\{"
        ),
        re.compile(
            r"(?P<prefix>\b)"
            r"(?P<name>[A-Za-z_$][\w$]*)\s*"
            r"\((?P<params>[^)]*)\)\s*\{"
        ),
    )
    _class_pattern = re.compile(
        r"\bclass\s+(?P<name>[A-Za-z_$][\w$]*)"
        r"(?:\s+extends\s+(?P<extends>[A-Za-z_$][\w$]*))?\s*\{"
    )
    _import_pattern = re.compile(
        r"(?:import\s+.+?\s+from\s+|require\s*\()\s*"
        r"['\"](?P<module>[^'\"]+)['\"]"
    )
    _dojo_pattern = re.compile(
        r"\b(?:define|require)\s*\(\s*\[(?P<modules>.*?)\]",
        re.DOTALL,
    )

    def parse(self, document: SourceDocument) -> dict[str, Any]:
        symbols: list[dict[str, Any]] = []
        claimed_ranges: list[tuple[int, int]] = []

        for match in self._class_pattern.finditer(document.content):
            end = _find_block_end(document.content, match.end() - 1)
            claimed_ranges.append((match.start(), end))
            symbols.append(
                _symbol(
                    document,
                    name=match.group("name"),
                    kind="class",
                    start=match.start(),
                    end=end,
                    extends=match.group("extends"),
                )
            )

        seen_functions: set[tuple[str, int]] = set()
        for pattern in self._function_patterns:
            for match in pattern.finditer(document.content):
                key = (match.group("name"), match.start())
                if key in seen_functions or _looks_like_control_statement(
                    document.content, match.start(), match.group("name")
                ):
                    continue

                seen_functions.add(key)
                end = _find_block_end(document.content, match.end() - 1)
                body = document.content[match.end() : end]
                symbols.append(
                    _symbol(
                        document,
                        name=match.group("name"),
                        kind="function",
                        start=match.start(),
                        end=end,
                        parameters=_split_parameters(match.group("params")),
                        calls=_extract_calls(body),
                        business_expressions=_extract_return_expressions(body),
                    )
                )

        imports = {
            match.group("module")
            for match in self._import_pattern.finditer(document.content)
        }
        for match in self._dojo_pattern.finditer(document.content):
            imports.update(re.findall(r"['\"]([^'\"]+)['\"]", match.group("modules")))

        return _artifact(
            document=document,
            parser_name="legacy-morph-javascript-parser",
            symbols=symbols,
            imports=sorted(imports),
            framework_hints=_javascript_framework_hints(document.content),
            warnings=_brace_warnings(document.content, claimed_ranges),
        )


class JavaParserAdapter:
    languages = frozenset({"Java"})

    _type_pattern = re.compile(
        r"(?P<visibility>public|protected|private)?\s*"
        r"(?P<modifiers>(?:(?:abstract|final|static)\s+)*)"
        r"(?P<kind>class|interface|enum)\s+"
        r"(?P<name>[A-Za-z_$][\w$]*)"
        r"(?:\s+extends\s+(?P<extends>[A-Za-z_$][\w$.,<>\s]*?))?"
        r"(?:\s+implements\s+(?P<implements>[A-Za-z_$][\w$.,<>\s]*?))?"
        r"\s*\{"
    )
    _method_pattern = re.compile(
        r"(?P<visibility>public|protected|private)?\s*"
        r"(?P<modifiers>(?:(?:static|final|abstract|synchronized|native)\s+)*)"
        r"(?P<return_type>[A-Za-z_$][\w$<>\[\],.? ]*)\s+"
        r"(?P<name>[A-Za-z_$][\w$]*)\s*"
        r"\((?P<params>[^)]*)\)\s*"
        r"(?:throws\s+[^{]+)?\{"
    )
    _import_pattern = re.compile(r"^\s*import\s+(?:static\s+)?([^;]+);", re.MULTILINE)

    def parse(self, document: SourceDocument) -> dict[str, Any]:
        symbols: list[dict[str, Any]] = []
        claimed_ranges: list[tuple[int, int]] = []
        type_names: set[str] = set()

        for match in self._type_pattern.finditer(document.content):
            end = _find_block_end(document.content, match.end() - 1)
            claimed_ranges.append((match.start(), end))
            type_names.add(match.group("name"))
            symbols.append(
                _symbol(
                    document,
                    name=match.group("name"),
                    kind=match.group("kind"),
                    start=match.start(),
                    end=end,
                    visibility=match.group("visibility"),
                    extends=_clean_optional(match.group("extends")),
                    implements=_split_types(match.group("implements")),
                )
            )

        for match in self._method_pattern.finditer(document.content):
            if _is_java_control_match(match.group("return_type"), match.group("name")):
                continue

            end = _find_block_end(document.content, match.end() - 1)
            body = document.content[match.end() : end]
            visibility, modifiers, return_type = _java_signature_parts(
                match.group("visibility"),
                match.group("modifiers"),
                match.group("return_type"),
            )
            is_constructor = match.group("name") in type_names and return_type is None
            symbols.append(
                _symbol(
                    document,
                    name=match.group("name"),
                    kind="constructor" if is_constructor else "method",
                    start=match.start(),
                    end=end,
                    visibility=visibility,
                    modifiers=modifiers,
                    parameters=_parse_java_parameters(match.group("params")),
                    return_type=return_type,
                    calls=_extract_calls(body),
                    business_expressions=_extract_return_expressions(body),
                )
            )

        imports = sorted(
            match.group(1).strip()
            for match in self._import_pattern.finditer(document.content)
        )
        return _artifact(
            document=document,
            parser_name="legacy-morph-java-parser",
            symbols=symbols,
            imports=imports,
            framework_hints=_java_framework_hints(document.content, imports),
            warnings=_brace_warnings(document.content, claimed_ranges),
        )


class ASTAgent:
    def __init__(
        self,
        artifact_root: str | Path = "artifacts",
        adapters: list[ParserAdapter] | None = None,
    ) -> None:
        self.artifact_root = Path(artifact_root)
        self.adapters = adapters or [
            JavaScriptParserAdapter(),
            JavaParserAdapter(),
        ]

    def generate(
        self,
        migration_session_id: str,
        documents: list[SourceDocument],
    ) -> dict[str, Any]:
        file_artifacts = [self._parse_document(document) for document in documents]
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "migration_session_id": migration_session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": file_artifacts,
            "summary": {
                "total_files": len(documents),
                "parsed_files": sum(
                    item["parse_status"] == "parsed" for item in file_artifacts
                ),
                "unsupported_files": sum(
                    item["parse_status"] == "unsupported" for item in file_artifacts
                ),
                "symbol_count": sum(
                    len(item.get("symbols", [])) for item in file_artifacts
                ),
            },
        }
        artifact_path = self._write_artifact(migration_session_id, artifact)
        return {
            "artifact_path": str(artifact_path),
            "artifact_hash": _sha256(artifact_path.read_text(encoding="utf-8")),
            "artifact": artifact,
        }

    def _parse_document(self, document: SourceDocument) -> dict[str, Any]:
        adapter = next(
            (
                candidate
                for candidate in self.adapters
                if document.language in candidate.languages
            ),
            None,
        )
        if adapter is None:
            return {
                "schema_version": SCHEMA_VERSION,
                "source_file": document.path,
                "language": document.language,
                "content_hash": _sha256(document.content),
                "parse_status": "unsupported",
                "parser": None,
                "symbols": [],
                "imports": [],
                "framework_hints": [],
                "warnings": [
                    f"No deterministic parser adapter for {document.language}."
                ],
            }
        return adapter.parse(document)

    def _write_artifact(
        self,
        migration_session_id: str,
        artifact: dict[str, Any],
    ) -> Path:
        directory = self.artifact_root / migration_session_id / "ast"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "normalized-ast.json"
        path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return path


def _artifact(
    document: SourceDocument,
    parser_name: str,
    symbols: list[dict[str, Any]],
    imports: list[str],
    framework_hints: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": document.path,
        "language": document.language,
        "content_hash": _sha256(document.content),
        "parse_status": "parsed",
        "parser": parser_name,
        "symbols": sorted(
            symbols,
            key=lambda item: item["source_range"]["start_line"],
        ),
        "imports": imports,
        "framework_hints": framework_hints,
        "warnings": warnings,
    }


def _symbol(
    document: SourceDocument,
    name: str,
    kind: str,
    start: int,
    end: int,
    **values: Any,
) -> dict[str, Any]:
    result = {
        "id": f"{document.path}:{name}:{_line_number(document.content, start)}",
        "name": name,
        "kind": kind,
        "source_range": {
            "start_line": _line_number(document.content, start),
            "end_line": _line_number(document.content, end),
        },
    }
    result.update(
        {
            key: value
            for key, value in values.items()
            if value not in (None, "", [])
        }
    )
    return result


def _find_block_end(content: str, opening_brace: int) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening_brace

    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
                continue
            index += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char == "/" and next_char == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1

    return len(content)


def _extract_calls(body: str) -> list[str]:
    excluded = {
        "catch",
        "for",
        "if",
        "new",
        "return",
        "super",
        "switch",
        "while",
    }
    calls = {
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z_$][\w$.]*)\s*\(", body)
        if match.group(1).split(".")[-1] not in excluded
    }
    return sorted(calls)


def _extract_return_expressions(body: str) -> list[str]:
    expressions = []
    for match in re.finditer(r"\breturn\s+(.+?);", body, re.DOTALL):
        expression = " ".join(match.group(1).split())
        if len(expression) <= 500:
            expressions.append(expression)
    return expressions


def _split_parameters(parameters: str) -> list[dict[str, str]]:
    result = []
    for parameter in _split_commas(parameters):
        cleaned = parameter.strip()
        if not cleaned:
            continue
        name = cleaned.split("=", 1)[0].strip()
        result.append({"name": name})
    return result


def _parse_java_parameters(parameters: str) -> list[dict[str, str]]:
    result = []
    for parameter in _split_commas(parameters):
        tokens = parameter.strip().split()
        if len(tokens) < 2:
            continue
        result.append(
            {
                "name": tokens[-1],
                "type": " ".join(tokens[:-1]),
            }
        )
    return result


def _split_commas(value: str) -> list[str]:
    items = []
    start = 0
    depth = 0
    for index, char in enumerate(value):
        if char in "<([{":
            depth += 1
        elif char in ">)]}":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            items.append(value[start:index])
            start = index + 1
    items.append(value[start:])
    return items


def _line_number(content: str, position: int) -> int:
    return content.count("\n", 0, position) + 1


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_optional(value: str | None) -> str | None:
    return " ".join(value.split()) if value else None


def _split_types(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _looks_like_control_statement(content: str, start: int, name: str) -> bool:
    if name in {"catch", "for", "if", "switch", "while"}:
        return True
    prefix = content[max(0, start - 12) : start]
    return bool(re.search(r"\b(?:if|for|while|switch|catch)\s*$", prefix))


def _is_java_control_match(return_type: str, name: str) -> bool:
    return return_type.strip() in {"if", "for", "while", "switch", "catch"} or name in {
        "if",
        "for",
        "while",
        "switch",
        "catch",
    }


def _java_signature_parts(
    visibility: str | None,
    modifiers: str,
    return_type: str,
) -> tuple[str | None, list[str], str | None]:
    tokens = return_type.split()
    if visibility is None and tokens and tokens[0] in {
        "private",
        "protected",
        "public",
    }:
        visibility = tokens.pop(0)

    modifier_values = modifiers.split()
    while tokens and tokens[0] in {
        "abstract",
        "final",
        "native",
        "static",
        "synchronized",
    }:
        modifier_values.append(tokens.pop(0))

    normalized_return_type = " ".join(tokens) or None
    return visibility, modifier_values, normalized_return_type


def _javascript_framework_hints(content: str) -> list[str]:
    hints = []
    lowered = content.lower()
    if re.search(r"\b(?:define|require)\s*\(\s*\[", content):
        hints.append("AMD")
    if "dojo/" in lowered or "dijit/" in lowered or "dojox/" in lowered:
        hints.append("Dojo")
    if "angular.module" in lowered:
        hints.append("AngularJS")
    if "backbone." in lowered:
        hints.append("Backbone.js")
    return hints


def _java_framework_hints(content: str, imports: list[str]) -> list[str]:
    searchable = f"{content}\n{' '.join(imports)}".lower()
    markers = {
        "javax.ejb": "Java EE",
        "javax.servlet": "Java Servlet",
        "org.apache.struts": "Apache Struts",
        "org.springframework": "Spring",
    }
    return sorted(
        framework
        for marker, framework in markers.items()
        if marker in searchable
    )


def _brace_warnings(
    content: str,
    claimed_ranges: list[tuple[int, int]],
) -> list[str]:
    warnings = []
    if content.count("{") != content.count("}"):
        warnings.append(
            "Unbalanced braces detected; source ranges may be incomplete."
        )
    if claimed_ranges and any(end == len(content) for _, end in claimed_ranges):
        warnings.append(
            "At least one block ended at end-of-file without a clear match."
        )
    return warnings
