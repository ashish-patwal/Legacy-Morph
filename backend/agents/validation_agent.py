from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ai_service import AIService


SCHEMA_VERSION = "1.0"


class ValidationAgentError(RuntimeError):
    pass


class ValidationAgent:
    def __init__(
        self,
        ai_service: AIService,
        artifact_root: str | Path = "artifacts",
    ) -> None:
        self.ai_service = ai_service
        self.artifact_root = Path(artifact_root)

    async def validate_file(
        self,
        migration_session_id: str,
        file_plan: dict[str, Any],
        generated_file: dict[str, Any],
        relevant_ast: dict[str, Any],
        dependency_schema: dict[str, Any],
        target_stack: dict[str, Any],
    ) -> dict[str, Any]:
        deterministic_report = deterministic_validate(
            file_plan,
            generated_file,
            target_stack,
        )
        llm_review = await self.ai_service.review_file(
            file_plan,
            generated_file,
            relevant_ast,
            dependency_schema,
            deterministic_report,
        )
        normalized_review = _normalize_llm_review(llm_review)
        overall_status = (
            "PASS"
            if deterministic_report["status"] == "PASS"
            and normalized_review["status"] == "PASS"
            else "FAIL"
        )
        report = {
            "schema_version": SCHEMA_VERSION,
            "migration_session_id": migration_session_id,
            "created_at": _utc_timestamp(),
            "target_path": generated_file.get("target_path"),
            "status": overall_status,
            "deterministic": deterministic_report,
            "llm_review": normalized_review,
            "findings": (
                deterministic_report["findings"]
                + normalized_review["findings"]
            ),
        }
        path = self._write_report(
            migration_session_id,
            str(generated_file.get("target_path", "generated-file")),
            report,
        )
        return {
            "artifact_path": str(path),
            "artifact_hash": _file_hash(path),
            "report": report,
        }

    def _write_report(
        self,
        migration_session_id: str,
        target_path: str,
        report: dict[str, Any],
    ) -> Path:
        directory = self.artifact_root / migration_session_id / "validation"
        directory.mkdir(parents=True, exist_ok=True)
        filename = target_path.replace("/", "__").replace("\\", "__")
        path = directory / f"{filename}.validation.json"
        path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        return path


def deterministic_validate(
    file_plan: dict[str, Any],
    generated_file: dict[str, Any],
    target_stack: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    target_path = str(generated_file.get("target_path", ""))
    content = generated_file.get("content")

    _validate_target_path(target_path, file_plan, findings)
    if not isinstance(content, str) or not content.strip():
        findings.append(
            _finding(
                "error",
                "Generated file content is empty.",
                target_path=target_path or None,
            )
        )
        return _deterministic_report(findings, [])

    language = str(target_stack.get("language", "")).strip()
    checks = [
        _content_size_check(content, target_path),
        _placeholder_check(content, target_path),
        _conflict_marker_check(content, target_path),
        _target_extension_check(language, target_path),
        _syntax_check(language, content, target_path),
        _acceptance_criteria_check(file_plan, content, target_path),
    ]
    check_results = []
    for check in checks:
        if check is None:
            continue
        check_results.append(check)
        findings.extend(check["findings"])

    unresolved = generated_file.get("unresolved_dependencies", [])
    if isinstance(unresolved, list) and unresolved:
        findings.append(
            _finding(
                "warning",
                "Generated file has unresolved dependencies: "
                + ", ".join(str(item) for item in unresolved),
                target_path=target_path,
            )
        )

    assumptions = generated_file.get("assumptions", [])
    if isinstance(assumptions, list):
        for assumption in assumptions:
            findings.append(
                _finding(
                    "info",
                    f"Generation assumption: {assumption}",
                    target_path=target_path,
                )
            )

    return _deterministic_report(findings, check_results)


def _validate_target_path(
    target_path: str,
    file_plan: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    expected_path = str(file_plan.get("target_path", ""))
    path = PurePosixPath(target_path)
    if not target_path or path.is_absolute() or ".." in path.parts:
        findings.append(
            _finding(
                "error",
                "Generated target path is unsafe.",
                target_path=target_path or None,
            )
        )
    if target_path != expected_path:
        findings.append(
            _finding(
                "error",
                "Generated target path does not match the approved plan.",
                target_path=target_path or None,
            )
        )


def _content_size_check(
    content: str,
    target_path: str,
) -> dict[str, Any]:
    maximum_size = 500_000
    passed = len(content.encode("utf-8")) <= maximum_size
    return _check(
        "content_size",
        passed,
        [] if passed else [
            _finding(
                "error",
                f"Generated file exceeds {maximum_size} bytes.",
                target_path=target_path,
            )
        ],
    )


def _placeholder_check(
    content: str,
    target_path: str,
) -> dict[str, Any]:
    patterns = {
        r"\bTODO\b": "TODO placeholder remains in generated code.",
        r"\bFIXME\b": "FIXME placeholder remains in generated code.",
        r"NotImplementedError": "NotImplementedError remains in generated code.",
        r"configure OPENAI_API_KEY": "Mock output was not replaced.",
    }
    findings = [
        _finding("error", message, target_path=target_path)
        for pattern, message in patterns.items()
        if re.search(pattern, content, re.IGNORECASE)
    ]
    return _check("placeholder_scan", not findings, findings)


def _conflict_marker_check(
    content: str,
    target_path: str,
) -> dict[str, Any]:
    markers = ("<<<<<<<", "=======", ">>>>>>>")
    found = [marker for marker in markers if marker in content]
    findings = []
    if found:
        findings.append(
            _finding(
                "error",
                "Merge conflict markers remain in generated code.",
                target_path=target_path,
            )
        )
    return _check("conflict_marker_scan", not findings, findings)


def _target_extension_check(
    language: str,
    target_path: str,
) -> dict[str, Any]:
    extensions = {
        "C#": {".cs"},
        "Go": {".go"},
        "Java": {".java"},
        "JavaScript": {".js", ".jsx", ".mjs", ".cjs"},
        "Kotlin": {".kt", ".kts"},
        "PHP": {".php"},
        "Python": {".py"},
        "Ruby": {".rb"},
        "TypeScript": {".ts", ".tsx"},
    }
    expected = extensions.get(language)
    if expected is None:
        return _check("target_extension", True, [])

    suffix = PurePosixPath(target_path).suffix.lower()
    passed = suffix in expected
    findings = [] if passed else [
        _finding(
            "error",
            f"Target extension {suffix or '(none)'} does not match {language}.",
            target_path=target_path,
        )
    ]
    return _check("target_extension", passed, findings)


def _syntax_check(
    language: str,
    content: str,
    target_path: str,
) -> dict[str, Any]:
    if language == "Python":
        try:
            ast.parse(content, filename=target_path)
        except SyntaxError as exc:
            return _check(
                "python_syntax",
                False,
                [
                    _finding(
                        "error",
                        f"Python syntax error on line {exc.lineno}: {exc.msg}",
                        target_path=target_path,
                    )
                ],
            )
        return _check("python_syntax", True, [])

    if language in {"JavaScript", "TypeScript", "Java", "C#", "Kotlin", "Go"}:
        findings = _balanced_delimiter_findings(content, target_path)
        return _check("balanced_delimiters", not findings, findings)

    return _check(
        "syntax",
        True,
        [
            _finding(
                "info",
                f"No deterministic syntax parser configured for {language}.",
                target_path=target_path,
            )
        ],
    )


def _balanced_delimiter_findings(
    content: str,
    target_path: str,
) -> list[dict[str, Any]]:
    pairs = {")": "(", "]": "[", "}": "{"}
    opening = set(pairs.values())
    stack = []
    quote: str | None = None
    escaped = False

    for character in content:
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character in opening:
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                return [
                    _finding(
                        "error",
                        "Generated code has unbalanced delimiters.",
                        target_path=target_path,
                    )
                ]

    if stack or quote:
        return [
            _finding(
                "error",
                "Generated code has unclosed delimiters or strings.",
                target_path=target_path,
            )
        ]
    return []


def _acceptance_criteria_check(
    file_plan: dict[str, Any],
    content: str,
    target_path: str,
) -> dict[str, Any]:
    criteria = file_plan.get("acceptance_criteria", [])
    symbols = file_plan.get("symbols_to_migrate", [])
    findings = []

    for symbol in symbols:
        simple_name = str(symbol).split(".")[-1]
        if simple_name and simple_name not in content:
            findings.append(
                _finding(
                    "warning",
                    f"Planned symbol is not visible in generated file: {symbol}",
                    target_path=target_path,
                )
            )

    if not criteria:
        findings.append(
            _finding(
                "warning",
                "File plan has no acceptance criteria.",
                target_path=target_path,
            )
        )
    return _check(
        "plan_traceability",
        not any(item["severity"] == "error" for item in findings),
        findings,
    )


def _normalize_llm_review(review: dict[str, Any]) -> dict[str, Any]:
    status = str(review.get("status", "FAIL")).upper()
    if status not in {"PASS", "FAIL"}:
        status = "FAIL"

    findings = []
    raw_findings = review.get("findings", [])
    if isinstance(raw_findings, list):
        for item in raw_findings:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity", "warning")).lower()
            if severity not in {"info", "warning", "error"}:
                severity = "warning"
            findings.append(
                _finding(
                    severity,
                    str(item.get("message", "Unspecified LLM review finding.")),
                    source_path=item.get("source_path"),
                    target_path=item.get("target_path"),
                )
            )

    if any(item["severity"] == "error" for item in findings):
        status = "FAIL"
    return {
        "status": status,
        "summary": str(review.get("summary", "")).strip(),
        "findings": findings,
    }


def _deterministic_report(
    findings: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    status = (
        "FAIL"
        if any(item["severity"] == "error" for item in findings)
        else "PASS"
    )
    return {
        "status": status,
        "checks": checks,
        "findings": findings,
    }


def _check(
    name: str,
    passed: bool,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "findings": findings,
    }


def _finding(
    severity: str,
    message: str,
    source_path: str | None = None,
    target_path: str | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "message": message,
        "source_path": source_path,
        "target_path": target_path,
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
