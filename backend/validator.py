from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any


TrustedExecutor = Callable[[dict[str, Any]], dict[str, Any]]


class ValidationError(RuntimeError):
    pass


def validate_test_cases(
    test_cases: list[dict[str, Any]],
    executor: TrustedExecutor,
    *,
    relative_tolerance: float = 1e-9,
    absolute_tolerance: float = 1e-9,
) -> dict[str, Any]:
    results = []

    for index, test_case in enumerate(test_cases, start=1):
        name = str(test_case.get("name") or f"test_{index}")
        test_input = test_case.get("input")
        expected = test_case.get("expected_output")

        if not isinstance(test_input, dict):
            results.append(
                _failed_result(
                    name,
                    expected,
                    None,
                    "Test input must be an object.",
                )
            )
            continue
        if not isinstance(expected, dict):
            results.append(
                _failed_result(
                    name,
                    expected,
                    None,
                    "Expected output must be an object.",
                )
            )
            continue

        try:
            actual = executor(test_input)
        except Exception as exc:
            results.append(
                _failed_result(
                    name,
                    expected,
                    None,
                    f"Trusted validation function failed: {exc}",
                )
            )
            continue

        if not isinstance(actual, dict):
            results.append(
                _failed_result(
                    name,
                    expected,
                    actual,
                    "Trusted validation function must return an object.",
                )
            )
            continue

        differences = compare_values(
            expected,
            actual,
            relative_tolerance=relative_tolerance,
            absolute_tolerance=absolute_tolerance,
        )
        results.append(
            {
                "test_name": name,
                "expected": expected,
                "actual": actual,
                "result": "PASS" if not differences else "FAIL",
                "differences": differences,
            }
        )

    passed = sum(result["result"] == "PASS" for result in results)
    failed = len(results) - passed
    return {
        "status": "PASS" if results and failed == 0 else "FAIL",
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def compare_values(
    expected: Any,
    actual: Any,
    *,
    path: str = "$",
    relative_tolerance: float = 1e-9,
    absolute_tolerance: float = 1e-9,
) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []

    if _is_number(expected) and _is_number(actual):
        if not math.isclose(
            float(expected),
            float(actual),
            rel_tol=relative_tolerance,
            abs_tol=absolute_tolerance,
        ):
            differences.append(_difference(path, expected, actual))
        return differences

    if type(expected) is not type(actual):
        differences.append(
            _difference(
                path,
                expected,
                actual,
                reason="Value types differ.",
            )
        )
        return differences

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)

        for missing_key in sorted(expected_keys - actual_keys):
            differences.append(
                _difference(
                    f"{path}.{missing_key}",
                    expected[missing_key],
                    None,
                    reason="Expected key is missing.",
                )
            )
        for extra_key in sorted(actual_keys - expected_keys):
            differences.append(
                _difference(
                    f"{path}.{extra_key}",
                    None,
                    actual[extra_key],
                    reason="Unexpected key is present.",
                )
            )
        for shared_key in sorted(expected_keys & actual_keys):
            differences.extend(
                compare_values(
                    expected[shared_key],
                    actual[shared_key],
                    path=f"{path}.{shared_key}",
                    relative_tolerance=relative_tolerance,
                    absolute_tolerance=absolute_tolerance,
                )
            )
        return differences

    if isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(
                _difference(
                    path,
                    len(expected),
                    len(actual),
                    reason="List lengths differ.",
                )
            )

        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual)
        ):
            differences.extend(
                compare_values(
                    expected_item,
                    actual_item,
                    path=f"{path}[{index}]",
                    relative_tolerance=relative_tolerance,
                    absolute_tolerance=absolute_tolerance,
                )
            )
        return differences

    if expected != actual:
        differences.append(_difference(path, expected, actual))
    return differences


def combine_validation_reports(
    behavioral_report: dict[str, Any],
    file_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    file_statuses = [
        str(report.get("status", "FAIL")).upper()
        for report in file_reports
    ]
    files_passed = bool(file_reports) and all(
        status == "PASS" for status in file_statuses
    )
    behavior_passed = behavioral_report.get("status") == "PASS"

    findings = []
    for report in file_reports:
        raw_findings = report.get("findings", [])
        if isinstance(raw_findings, list):
            findings.extend(
                finding
                for finding in raw_findings
                if isinstance(finding, dict)
            )

    return {
        "status": "PASS" if files_passed and behavior_passed else "FAIL",
        "behavioral": behavioral_report,
        "files": file_reports,
        "summary": {
            "total_files": len(file_reports),
            "passed_files": sum(
                status == "PASS" for status in file_statuses
            ),
            "failed_files": sum(
                status != "PASS" for status in file_statuses
            ),
            "total_tests": int(behavioral_report.get("total_tests", 0)),
            "passed_tests": int(behavioral_report.get("passed", 0)),
            "failed_tests": int(behavioral_report.get("failed", 0)),
        },
        "findings": findings,
    }


def loan_calculator_executor(test_input: dict[str, Any]) -> dict[str, Any]:
    principal = _required_number(test_input, "principal")
    rate = _required_number(test_input, "rate")
    years = _required_number(test_input, "years")

    interest = principal * rate * years / 100
    return {
        "interest": interest,
        "total_amount": principal + interest,
    }


def _required_number(test_input: dict[str, Any], field: str) -> float:
    value = test_input.get(field)
    if not _is_number(value):
        raise ValidationError(f"{field} must be numeric.")
    return float(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _difference(
    path: str,
    expected: Any,
    actual: Any,
    reason: str = "Values differ.",
) -> dict[str, Any]:
    return {
        "path": path,
        "expected": expected,
        "actual": actual,
        "reason": reason,
    }


def _failed_result(
    name: str,
    expected: Any,
    actual: Any,
    reason: str,
) -> dict[str, Any]:
    return {
        "test_name": name,
        "expected": expected,
        "actual": actual,
        "result": "FAIL",
        "differences": [
            _difference("$", expected, actual, reason=reason),
        ],
    }
