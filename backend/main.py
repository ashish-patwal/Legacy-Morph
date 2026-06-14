from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.ast_agent import ASTAgent, SourceDocument
from agents.dependency_agent import DependencyAgent
from agents.migration_agent import MigrationAgent, MigrationAgentError
from agents.validation_agent import ValidationAgent
from ai_service import AIService, AIServiceError
from database import create_tables, get_db
from github_mcp_service import (
    GitHubMCPError,
    GitHubMCPService,
    InvalidRepositoryUrlError,
)
from models import GeneratedFile, MigrationSession, ValidationResult
from schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    FileReviewRequest,
    GenerateTestsRequest,
    GenerateTestsResponse,
    GeneratedFileResponse,
    MigrationSessionCreate,
    MigrationSessionResponse,
    MigrateRequest,
    RepositoryInspectRequest,
    RepositoryInspectResponse,
    ValidateRequest,
    ValidationFinding,
    ValidationResponse,
)
from validator import loan_calculator_executor, validate_test_cases


class AppSettings(BaseSettings):
    artifact_root: str = "./artifacts"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = AppSettings()
ai_service = AIService()
github_service = GitHubMCPService()
ast_agent = ASTAgent(settings.artifact_root)
dependency_agent = DependencyAgent(settings.artifact_root)
migration_agent = MigrationAgent(ai_service, settings.artifact_root)
validation_agent = ValidationAgent(ai_service, settings.artifact_root)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield
    await github_service.close()


app = FastAPI(
    title="Legacy-Morph API",
    version="0.1.0",
    description="AST-driven legacy application migration MVP.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "legacy-morph-backend",
        "ai_mode": "mock" if ai_service.is_mock else "openai",
    }


@app.post(
    "/repositories/inspect",
    response_model=RepositoryInspectResponse,
)
async def inspect_repository(
    request: RepositoryInspectRequest,
) -> RepositoryInspectResponse:
    try:
        return await github_service.inspect_repository(
            str(request.repository_url),
            request.branch,
        )
    except InvalidRepositoryUrlError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GitHubMCPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(
    "/migration-sessions",
    response_model=MigrationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_migration_session(
    request: MigrationSessionCreate,
    database: Session = Depends(get_db),
) -> MigrationSessionResponse:
    session = MigrationSession(
        repository_url=str(request.repository_url),
        branch=request.branch,
        commit_sha=request.commit_sha,
        status="created",
        current_step="analysis",
        selected_files_json=_dump_json(request.selected_files),
        target_stack_json=_dump_json(request.target.model_dump()),
    )
    database.add(session)
    database.commit()
    database.refresh(session)
    return _session_response(session)


@app.get(
    "/migration-sessions/{session_id}",
    response_model=MigrationSessionResponse,
)
def get_migration_session(
    session_id: str,
    database: Session = Depends(get_db),
) -> MigrationSessionResponse:
    return _session_response(_get_session(database, session_id))


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    request: AnalyzeRequest,
    database: Session = Depends(get_db),
) -> AnalysisResponse:
    session = _get_session(database, request.migration_session_id)
    documents = await _load_selected_documents(session)

    ast_result = ast_agent.generate(session.id, documents)
    dependency_result = dependency_agent.generate(
        session.id,
        ast_result["artifact"],
    )
    manifest = _load_json(session.repository_manifest_json, {})
    if not manifest:
        manifest = _manifest_from_documents(session, documents)

    try:
        analysis_result = await migration_agent.analyze(
            session.id,
            manifest,
            ast_result["artifact"],
            dependency_result["artifact"],
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    analysis = analysis_result["analysis"]
    session.ast_artifact_path = ast_result["artifact_path"]
    session.dependency_schema_path = dependency_result["artifact_path"]
    session.source_technologies_json = _dump_json(
        analysis["source_technologies"]
    )
    session.status = "analyzed"
    session.current_step = "migration_plan"
    database.commit()

    return AnalysisResponse(
        migration_session_id=session.id,
        summary=analysis["summary"],
        source_technologies=analysis["source_technologies"],
        functions=analysis["functions"],
        business_rules=analysis["business_rules"],
        risks=analysis["risks"],
        ast_artifact_path=session.ast_artifact_path,
        dependency_schema_path=session.dependency_schema_path,
    )


@app.post("/migration-sessions/{session_id}/plan")
async def create_migration_plan(
    session_id: str,
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    session = _get_session(database, session_id)
    ast_artifact = _read_json_artifact(session.ast_artifact_path)
    dependency_schema = _read_json_artifact(session.dependency_schema_path)
    analysis = _read_analysis_artifact(session.id)

    try:
        result = await migration_agent.create_plan(
            session.id,
            analysis,
            ast_artifact,
            dependency_schema,
            _load_json(session.target_stack_json, {}),
        )
    except (AIServiceError, MigrationAgentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.migration_plan_json = _dump_json(result["artifact"])
    session.status = "plan_created"
    session.current_step = "plan_approval"
    database.commit()
    return result["artifact"]


@app.post("/migration-sessions/{session_id}/plan/approve")
def approve_migration_plan(
    session_id: str,
    database: Session = Depends(get_db),
) -> dict[str, Any]:
    session = _get_session(database, session_id)
    plan_artifact = _load_json(session.migration_plan_json, {})
    if not plan_artifact:
        raise HTTPException(status_code=409, detail="Migration plan is missing.")

    approved = migration_agent.approve_plan(plan_artifact)
    session.migration_plan_json = _dump_json(approved)
    session.status = "plan_approved"
    session.current_step = "file_generation"
    database.commit()
    return approved


@app.post("/migrate", response_model=GeneratedFileResponse)
async def migrate(
    request: MigrateRequest,
    database: Session = Depends(get_db),
) -> GeneratedFileResponse:
    session = _get_session(database, request.migration_session_id)
    plan_artifact = _load_json(session.migration_plan_json, {})
    documents = await _load_selected_documents(session)
    source_documents = [
        {
            "path": document.path,
            "language": document.language,
            "content": document.content,
        }
        for document in documents
    ]
    ast_artifact = _read_json_artifact(session.ast_artifact_path)
    dependency_schema = _read_json_artifact(session.dependency_schema_path)
    approved_files = [
        _generated_file_context(file)
        for file in session.generated_files
        if file.status == "approved"
    ]

    try:
        result = await migration_agent.generate_next_file(
            session.id,
            plan_artifact,
            source_documents,
            ast_artifact,
            dependency_schema,
            approved_files,
        )
    except (AIServiceError, MigrationAgentError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    generated = result["generated_file"]
    record = GeneratedFile(
        migration_session_id=session.id,
        source_paths_json=_dump_json(generated["source_paths"]),
        target_path=generated["target_path"],
        content=generated["content"],
        status="generated",
    )
    database.add(record)
    session.status = "file_generated"
    session.current_step = "file_validation"
    database.commit()
    database.refresh(record)
    return _generated_file_response(record)


@app.post(
    "/generated-files/{file_id}/review",
    response_model=GeneratedFileResponse,
)
def review_generated_file(
    file_id: str,
    request: FileReviewRequest,
    database: Session = Depends(get_db),
) -> GeneratedFileResponse:
    generated_file = _get_generated_file(database, file_id)
    generated_file.status = request.decision
    generated_file.review_comments = request.comments

    session = generated_file.migration_session
    session.status = f"file_{request.decision}"
    session.current_step = (
        "file_generation"
        if request.decision == "approved"
        else "file_revision"
    )
    database.commit()
    database.refresh(generated_file)
    return _generated_file_response(generated_file)


@app.post("/generate-tests", response_model=GenerateTestsResponse)
async def generate_tests(
    request: GenerateTestsRequest,
    database: Session = Depends(get_db),
) -> GenerateTestsResponse:
    session = _get_session(database, request.migration_session_id)
    generated_files = _requested_generated_files(
        database,
        session.id,
        request.generated_file_ids,
    )
    analysis = _read_analysis_artifact(session.id)

    try:
        result = await ai_service.generate_tests(
            analysis.get("business_rules", []),
            [_generated_file_context(file) for file in generated_files],
            _load_json(session.target_stack_json, {}),
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session.status = "tests_generated"
    session.current_step = "validation"
    database.commit()
    return GenerateTestsResponse(
        migration_session_id=session.id,
        test_cases=result.get("test_cases", []),
    )


@app.post("/validate", response_model=ValidationResponse)
async def validate(
    request: ValidateRequest,
    database: Session = Depends(get_db),
) -> ValidationResponse:
    session = _get_session(database, request.migration_session_id)
    generated_files = _requested_generated_files(
        database,
        session.id,
        request.generated_file_ids,
    )
    ast_artifact = _read_json_artifact(session.ast_artifact_path)
    dependency_schema = _read_json_artifact(session.dependency_schema_path)
    plan_artifact = _load_json(session.migration_plan_json, {})
    target_stack = _load_json(session.target_stack_json, {})

    file_reports = []
    for generated_file in generated_files:
        file_plan = _find_file_plan(
            plan_artifact,
            generated_file.target_path,
        )
        generated_context = _generated_file_context(generated_file)
        relevant_ast = _filter_ast(
            ast_artifact,
            set(generated_context["source_paths"]),
        )
        try:
            result = await validation_agent.validate_file(
                session.id,
                file_plan,
                generated_context,
                relevant_ast,
                dependency_schema,
                target_stack,
            )
        except AIServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        file_report = result["report"]
        file_reports.append(file_report)
        _store_validation_result(
            database,
            generated_file.id,
            "deterministic",
            file_report["deterministic"],
        )
        _store_validation_result(
            database,
            generated_file.id,
            "llm_review",
            file_report["llm_review"],
        )

    test_cases = [test.model_dump() for test in request.test_cases]
    behavioral = _behavioral_validation(test_cases)
    file_status = all(report["status"] == "PASS" for report in file_reports)
    overall_status = (
        "PASS"
        if file_status and behavioral["status"] == "PASS"
        else "FAIL"
    )
    findings = _response_findings(file_reports)

    session.status = (
        "validation_passed"
        if overall_status == "PASS"
        else "validation_failed"
    )
    session.current_step = (
        "file_review" if overall_status == "PASS" else "file_revision"
    )
    database.commit()

    return ValidationResponse(
        migration_session_id=session.id,
        status=overall_status,
        deterministic_status=(
            "PASS"
            if all(
                report["deterministic"]["status"] == "PASS"
                for report in file_reports
            )
            else "FAIL"
        ),
        llm_review_status=(
            "PASS"
            if all(
                report["llm_review"]["status"] == "PASS"
                for report in file_reports
            )
            else "FAIL"
        ),
        total_tests=behavioral["total_tests"],
        passed=behavioral["passed"],
        failed=behavioral["failed"],
        findings=findings,
    )


async def _load_selected_documents(
    session: MigrationSession,
) -> list[SourceDocument]:
    selected_paths = _load_json(session.selected_files_json, [])
    manifest = _load_json(session.repository_manifest_json, {})
    cached_contents = manifest.get("file_contents", {})
    documents = []

    for path in selected_paths:
        content = cached_contents.get(path)
        if not isinstance(content, str):
            content = await _fetch_file_content(session, path)
        documents.append(
            SourceDocument(
                path=path,
                language=_language_for_path(path),
                content=content,
            )
        )
    return documents


async def _fetch_file_content(
    session: MigrationSession,
    path: str,
) -> str:
    try:
        return await github_service.get_file_content(
            repository_url=session.repository_url,
            path=path,
            branch=session.branch,
            commit_sha=session.commit_sha,
        )
    except GitHubMCPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _manifest_from_documents(
    session: MigrationSession,
    documents: list[SourceDocument],
) -> dict[str, Any]:
    return {
        "repository_url": session.repository_url,
        "branch": session.branch,
        "commit_sha": session.commit_sha,
        "files": [
            {
                "path": document.path,
                "language": document.language,
                "size_bytes": len(document.content.encode("utf-8")),
            }
            for document in documents
        ],
        "source_technologies": _load_json(
            session.source_technologies_json,
            [],
        ),
    }


def _get_session(database: Session, session_id: str) -> MigrationSession:
    session = database.get(MigrationSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Migration session not found.")
    return session


def _get_generated_file(
    database: Session,
    file_id: str,
) -> GeneratedFile:
    generated_file = database.get(GeneratedFile, file_id)
    if generated_file is None:
        raise HTTPException(status_code=404, detail="Generated file not found.")
    return generated_file


def _requested_generated_files(
    database: Session,
    session_id: str,
    file_ids: list[str],
) -> list[GeneratedFile]:
    records = list(
        database.scalars(
            select(GeneratedFile).where(
                GeneratedFile.migration_session_id == session_id,
                GeneratedFile.id.in_(file_ids),
            )
        )
    )
    if len(records) != len(set(file_ids)):
        raise HTTPException(
            status_code=404,
            detail="One or more generated files were not found.",
        )
    return records


def _session_response(
    session: MigrationSession,
) -> MigrationSessionResponse:
    return MigrationSessionResponse(
        id=session.id,
        repository_url=session.repository_url,
        branch=session.branch,
        commit_sha=session.commit_sha,
        status=session.status,
        current_step=session.current_step,
        selected_files=_load_json(session.selected_files_json, []),
        target=_load_json(session.target_stack_json, {}),
        source_technologies=_load_json(
            session.source_technologies_json,
            [],
        ),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _generated_file_response(
    generated_file: GeneratedFile,
) -> GeneratedFileResponse:
    return GeneratedFileResponse(
        id=generated_file.id,
        migration_session_id=generated_file.migration_session_id,
        source_paths=_load_json(generated_file.source_paths_json, []),
        target_path=generated_file.target_path,
        content=generated_file.content,
        status=generated_file.status,
        review_comments=generated_file.review_comments,
        created_at=generated_file.created_at,
        updated_at=generated_file.updated_at,
    )


def _generated_file_context(
    generated_file: GeneratedFile,
) -> dict[str, Any]:
    return {
        "id": generated_file.id,
        "target_path": generated_file.target_path,
        "content": generated_file.content,
        "source_paths": _load_json(
            generated_file.source_paths_json,
            [],
        ),
        "status": generated_file.status,
        "review_comments": generated_file.review_comments,
        "assumptions": [],
        "unresolved_dependencies": [],
    }


def _store_validation_result(
    database: Session,
    generated_file_id: str,
    validation_type: str,
    report: dict[str, Any],
) -> None:
    database.add(
        ValidationResult(
            generated_file_id=generated_file_id,
            validation_type=validation_type,
            status=report.get("status", "FAIL"),
            summary=report.get("summary", f"{validation_type} completed."),
            details_json=_dump_json(report),
        )
    )


def _behavioral_validation(
    test_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    loan_fields = {"principal", "rate", "years"}
    if test_cases and all(
        loan_fields.issubset(test_case.get("input", {}))
        for test_case in test_cases
    ):
        return validate_test_cases(test_cases, loan_calculator_executor)
    return {
        "status": "FAIL",
        "total_tests": len(test_cases),
        "passed": 0,
        "failed": len(test_cases),
        "results": [],
    }


def _find_file_plan(
    plan_artifact: dict[str, Any],
    target_path: str,
) -> dict[str, Any]:
    for file_plan in plan_artifact.get("plan", {}).get("files", []):
        if file_plan.get("target_path") == target_path:
            return file_plan
    raise HTTPException(
        status_code=409,
        detail=f"No approved plan entry for {target_path}.",
    )


def _filter_ast(
    ast_artifact: dict[str, Any],
    source_paths: set[str],
) -> dict[str, Any]:
    return {
        "schema_version": ast_artifact.get("schema_version"),
        "files": [
            item
            for item in ast_artifact.get("files", [])
            if item.get("source_file") in source_paths
        ],
    }


def _response_findings(
    file_reports: list[dict[str, Any]],
) -> list[ValidationFinding]:
    findings = []
    for report in file_reports:
        for item in report.get("findings", []):
            findings.append(ValidationFinding.model_validate(item))
    return findings


def _read_analysis_artifact(session_id: str) -> dict[str, Any]:
    path = (
        Path(settings.artifact_root)
        / session_id
        / "analysis"
        / "analysis.json"
    )
    artifact = _read_json_artifact(str(path))
    return artifact.get("analysis", {})


def _read_json_artifact(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        raise HTTPException(status_code=409, detail="Required artifact is missing.")
    path = Path(path_value)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read artifact: {path}",
        ) from exc


def _load_json(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _language_for_path(path: str) -> str:
    language_by_extension = {
        ".c": "C",
        ".cbl": "COBOL",
        ".cob": "COBOL",
        ".cpp": "C++",
        ".cs": "C#",
        ".go": "Go",
        ".java": "Java",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".kt": "Kotlin",
        ".php": "PHP",
        ".pl": "Perl",
        ".py": "Python",
        ".rb": "Ruby",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".vb": "Visual Basic",
    }
    return language_by_extension.get(
        Path(path).suffix.lower(),
        "Unknown",
    )

