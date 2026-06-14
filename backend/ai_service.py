from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from pydantic_settings import BaseSettings, SettingsConfigDict

from prompts import (
    build_analysis_prompt,
    build_file_generation_prompt,
    build_independent_review_prompt,
    build_migration_plan_prompt,
    build_test_generation_prompt,
)


class AIServiceError(RuntimeError):
    pass


class AISettings(BaseSettings):
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_max_output_tokens: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def mock_mode(self) -> bool:
        key = (self.openai_api_key or "").strip()
        return not key or key == "your_openai_api_key_here"


class AIService:
    def __init__(
        self,
        settings: AISettings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or AISettings()
        self._client = client

        if self.settings.llm_provider.lower() != "openai":
            raise AIServiceError(
                f"Unsupported LLM provider: {self.settings.llm_provider}"
            )

        if not self.settings.mock_mode and self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    @property
    def is_mock(self) -> bool:
        return self.settings.mock_mode

    async def analyze_code(
        self,
        repository_manifest: dict[str, Any],
        ast_artifact: dict[str, Any],
        dependency_schema: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = build_analysis_prompt(
            repository_manifest,
            ast_artifact,
            dependency_schema,
        )
        return await self._generate_json(
            prompt,
            _mock_analysis(repository_manifest),
        )

    async def create_migration_plan(
        self,
        analysis: dict[str, Any],
        ast_artifact: dict[str, Any],
        dependency_schema: dict[str, Any],
        target_stack: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = build_migration_plan_prompt(
            analysis,
            ast_artifact,
            dependency_schema,
            target_stack,
        )
        return await self._generate_json(
            prompt,
            _mock_migration_plan(target_stack),
        )

    async def generate_file(
        self,
        target_stack: dict[str, Any],
        file_plan: dict[str, Any],
        source_slices: list[dict[str, Any]],
        relevant_ast: dict[str, Any],
        relevant_dependencies: dict[str, Any],
        approved_files: list[dict[str, Any]],
        review_comments: str | None = None,
    ) -> dict[str, Any]:
        prompt = build_file_generation_prompt(
            target_stack,
            file_plan,
            source_slices,
            relevant_ast,
            relevant_dependencies,
            approved_files,
            review_comments,
        )
        return await self._generate_json(
            prompt,
            _mock_generated_file(target_stack, file_plan),
        )

    async def generate_tests(
        self,
        business_rules: list[str],
        generated_files: list[dict[str, Any]],
        target_stack: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = build_test_generation_prompt(
            business_rules,
            generated_files,
            target_stack,
        )
        return await self._generate_json(prompt, _mock_tests())

    async def review_file(
        self,
        file_plan: dict[str, Any],
        generated_file: dict[str, Any],
        relevant_ast: dict[str, Any],
        dependency_schema: dict[str, Any],
        deterministic_report: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = build_independent_review_prompt(
            file_plan,
            generated_file,
            relevant_ast,
            dependency_schema,
            deterministic_report,
        )
        return await self._generate_json(
            prompt,
            _mock_review(deterministic_report),
        )

    async def _generate_json(
        self,
        prompt: str,
        mock_response: dict[str, Any],
    ) -> dict[str, Any]:
        if self.settings.mock_mode:
            return mock_response
        if self._client is None:
            raise AIServiceError("OpenAI client is not configured.")

        try:
            response = await self._client.responses.create(
                model=self.settings.openai_model,
                input=prompt,
                max_output_tokens=self.settings.openai_max_output_tokens,
            )
        except OpenAIError as exc:
            raise AIServiceError(f"OpenAI request failed: {exc}") from exc

        return _parse_json_response(response.output_text)


def _parse_json_response(output_text: str) -> dict[str, Any]:
    text = output_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIServiceError("OpenAI returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise AIServiceError("OpenAI response must be a JSON object.")
    return parsed


def _mock_analysis(repository_manifest: dict[str, Any]) -> dict[str, Any]:
    technologies = repository_manifest.get("source_technologies", [])
    return {
        "summary": (
            "Mock analysis completed. Configure OPENAI_API_KEY for semantic "
            "repository analysis."
        ),
        "source_technologies": technologies,
        "functions": [],
        "business_rules": [],
        "repeated_patterns": [],
        "risks": [
            "Mock mode cannot infer complete business behavior.",
        ],
        "unknowns": [
            "Function semantics require an OpenAI API key or deterministic "
            "language analyzers."
        ],
    }


def _mock_migration_plan(target_stack: dict[str, Any]) -> dict[str, Any]:
    language = target_stack.get("language", "Unknown")
    framework = target_stack.get("framework")
    target_summary = f"{language}"
    if framework:
        target_summary += f" with {framework}"

    return {
        "target_summary": target_summary,
        "support_level": "experimental",
        "architecture_notes": [
            "Mock plan created without semantic LLM analysis.",
        ],
        "files": [
            {
                "order": 1,
                "target_path": _default_target_path(language),
                "source_paths": [],
                "purpose": "Demonstrate one-file migration flow.",
                "depends_on": [],
                "symbols_to_migrate": [],
                "acceptance_criteria": [
                    "Generated file uses the selected target language.",
                    "Human review is required.",
                ],
            }
        ],
        "unresolved_questions": [
            "Configure OPENAI_API_KEY to generate a repository-specific plan."
        ],
        "risks": [
            "Mock plan does not guarantee behavioral equivalence.",
        ],
    }


def _mock_generated_file(
    target_stack: dict[str, Any],
    file_plan: dict[str, Any],
) -> dict[str, Any]:
    language = target_stack.get("language", "Unknown")
    target_path = file_plan.get("target_path") or _default_target_path(language)
    content = _mock_file_content(language)
    return {
        "target_path": target_path,
        "content": content,
        "source_paths": file_plan.get("source_paths", []),
        "source_to_target_map": [],
        "assumptions": [
            "This placeholder was generated in mock mode.",
        ],
        "unresolved_dependencies": [
            "Configure OPENAI_API_KEY for real code generation.",
        ],
    }


def _mock_tests() -> dict[str, Any]:
    return {
        "test_cases": [
            {
                "name": "mock_generation_requires_review",
                "input": {"mock_mode": True},
                "expected_output": {"human_review_required": True},
            }
        ]
    }


def _mock_review(
    deterministic_report: dict[str, Any],
) -> dict[str, Any]:
    deterministic_status = deterministic_report.get("status", "FAIL")
    status = "PASS" if deterministic_status == "PASS" else "FAIL"
    findings = []
    if status == "FAIL":
        findings.append(
            {
                "severity": "error",
                "message": "Deterministic validation did not pass.",
                "source_path": None,
                "target_path": None,
            }
        )
    return {
        "status": status,
        "summary": "Mock review mirrors deterministic validation.",
        "findings": findings,
    }


def _default_target_path(language: str) -> str:
    extension_by_language = {
        "C#": ".cs",
        "Go": ".go",
        "Java": ".java",
        "JavaScript": ".js",
        "Kotlin": ".kt",
        "PHP": ".php",
        "Python": ".py",
        "Ruby": ".rb",
        "TypeScript": ".ts",
    }
    extension = extension_by_language.get(language, ".txt")
    return f"generated/main{extension}"


def _mock_file_content(language: str) -> str:
    comments = {
        "C#": "//",
        "Go": "//",
        "Java": "//",
        "JavaScript": "//",
        "Kotlin": "//",
        "PHP": "//",
        "Python": "#",
        "Ruby": "#",
        "TypeScript": "//",
    }
    prefix = comments.get(language, "#")
    return (
        f"{prefix} Mock {language} migration output.\n"
        f"{prefix} Configure OPENAI_API_KEY for real code generation.\n"
    )
