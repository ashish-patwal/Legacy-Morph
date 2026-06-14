from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

from schemas import RepositoryFile, RepositoryInspectResponse, SourceTechnology


SUPPORTED_EXTENSIONS = {
    ".c": "C",
    ".cc": "C++",
    ".cbl": "COBOL",
    ".cob": "COBOL",
    ".cpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".pas": "Pascal",
    ".perl": "Perl",
    ".php": "PHP",
    ".pl": "Perl",
    ".py": "Python",
    ".rb": "Ruby",
    ".scala": "Scala",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vb": "Visual Basic",
}

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".next",
    ".venv",
    ".vscode",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}

FRAMEWORK_MARKERS = {
    "dojo/": ("JavaScript", "Dojo"),
    "dijit/": ("JavaScript", "Dojo"),
    "dojox/": ("JavaScript", "Dojo"),
    "angular.module": ("JavaScript", "AngularJS"),
    "backbone.": ("JavaScript", "Backbone.js"),
    "org.apache.struts": ("Java", "Apache Struts"),
    "org.springframework": ("Java", "Spring"),
    "javax.ejb": ("Java", "Java EE"),
    "javax.servlet": ("Java", "Java Servlet"),
}

SAFE_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")


class GitHubRepositoryError(RuntimeError):
    pass


class InvalidRepositoryUrlError(GitHubRepositoryError):
    pass


# Backward-compatible name while routes and docs transition away from MCP.
GitHubMCPError = GitHubRepositoryError


class RepositorySettings(BaseSettings):
    github_max_files: int = 100
    github_max_file_size_bytes: int = 200_000
    github_max_repository_size_bytes: int = 25_000_000
    github_clone_timeout_seconds: int = 60
    repository_temp_root: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.full_name}.git"


@dataclass
class RepositoryCheckout:
    repository: GitHubRepository
    requested_branch: str | None
    branch: str
    commit_sha: str
    path: Path


class GitHubRepositoryService:
    def __init__(self, settings: RepositorySettings | None = None) -> None:
        self.settings = settings or RepositorySettings()
        self._checkouts: dict[str, RepositoryCheckout] = {}
        self._lock = asyncio.Lock()
        self._temp_root = Path(
            tempfile.mkdtemp(
                prefix="legacy-morph-repositories-",
                dir=self.settings.repository_temp_root,
            )
        )

    async def inspect_repository(
        self,
        repository_url: str,
        branch: str | None = None,
    ) -> RepositoryInspectResponse:
        checkout = await self._checkout(repository_url, branch)
        all_entries = self._repository_entries(checkout.path)
        entries = all_entries[: self.settings.github_max_files]
        files = [
            self._to_repository_file(checkout.path, entry)
            for entry in entries
        ]
        technologies = detect_source_technologies(checkout.path, files)
        warnings = self._warnings(files, all_entries)

        return RepositoryInspectResponse(
            repository=checkout.repository.full_name,
            branch=checkout.branch,
            commit_sha=checkout.commit_sha,
            files=files,
            source_technologies=technologies,
            warnings=warnings,
        )

    async def get_file_content(
        self,
        repository_url: str,
        path: str,
        branch: str | None = None,
        commit_sha: str | None = None,
    ) -> str:
        checkout = await self._checkout(repository_url, branch)
        if commit_sha and checkout.commit_sha != commit_sha:
            raise GitHubRepositoryError(
                "Repository commit changed after inspection. Start a new session."
            )

        relative_path = _safe_relative_path(path)
        file_path = (checkout.path / relative_path).resolve()
        checkout_root = checkout.path.resolve()
        if checkout_root not in file_path.parents:
            raise GitHubRepositoryError("Requested file is outside the checkout.")
        if not file_path.is_file():
            raise GitHubRepositoryError(f"Repository file not found: {path}")
        if file_path.stat().st_size > self.settings.github_max_file_size_bytes:
            raise GitHubRepositoryError(
                f"Repository file exceeds the size limit: {path}"
            )

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise GitHubRepositoryError(
                f"Repository file is not UTF-8 text: {path}"
            ) from exc

    async def close(self) -> None:
        self._checkouts.clear()
        await asyncio.to_thread(shutil.rmtree, self._temp_root, True)

    async def _checkout(
        self,
        repository_url: str,
        branch: str | None,
    ) -> RepositoryCheckout:
        repository = parse_github_repository_url(repository_url)
        normalized_branch = _validate_branch(branch)
        cache_key = f"{repository.full_name}@{normalized_branch or 'default'}"

        async with self._lock:
            cached = self._checkouts.get(cache_key)
            if cached and cached.path.exists():
                return cached

            checkout_path = self._temp_root / hashlib.sha256(
                cache_key.encode("utf-8")
            ).hexdigest()[:20]
            checkout = await self._clone(
                repository,
                normalized_branch,
                checkout_path,
            )
            self._checkouts[cache_key] = checkout
            return checkout

    async def _clone(
        self,
        repository: GitHubRepository,
        branch: str | None,
        checkout_path: Path,
    ) -> RepositoryCheckout:
        command = [
            "git",
            "-c",
            "protocol.file.allow=never",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--no-tags",
        ]
        if branch:
            command.extend(["--branch", branch])
        command.extend([repository.clone_url, str(checkout_path)])

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.settings.github_clone_timeout_seconds,
            )
        except TimeoutError as exc:
            if "process" in locals():
                process.kill()
                await process.communicate()
            shutil.rmtree(checkout_path, ignore_errors=True)
            raise GitHubRepositoryError("Repository clone timed out.") from exc
        except OSError as exc:
            raise GitHubRepositoryError(
                "Git is unavailable on the backend server."
            ) from exc

        if process.returncode != 0:
            shutil.rmtree(checkout_path, ignore_errors=True)
            message = stderr.decode("utf-8", errors="replace").strip()
            raise GitHubRepositoryError(
                f"Could not clone the public repository: {message}"
            )

        repository_size = sum(
            file.stat().st_size
            for file in checkout_path.rglob("*")
            if file.is_file() and ".git" not in file.parts
        )
        if repository_size > self.settings.github_max_repository_size_bytes:
            shutil.rmtree(checkout_path, ignore_errors=True)
            raise GitHubRepositoryError(
                "Repository exceeds the configured MVP size limit."
            )

        commit_sha = await _git_output(checkout_path, "rev-parse", "HEAD")
        resolved_branch = await _git_output(
            checkout_path,
            "branch",
            "--show-current",
        )
        return RepositoryCheckout(
            repository=repository,
            requested_branch=branch,
            branch=resolved_branch or branch or "main",
            commit_sha=commit_sha,
            path=checkout_path,
        )

    def _repository_entries(self, checkout_path: Path) -> list[Path]:
        entries = []
        for path in sorted(checkout_path.rglob("*")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(checkout_path)
            if _is_ignored_path(relative_path.as_posix()):
                continue
            entries.append(relative_path)
        return entries

    def _to_repository_file(
        self,
        checkout_path: Path,
        relative_path: Path,
    ) -> RepositoryFile:
        full_path = checkout_path / relative_path
        size = full_path.stat().st_size
        path = relative_path.as_posix()
        language = SUPPORTED_EXTENSIONS.get(relative_path.suffix.lower())
        supported = (
            language is not None
            and size <= self.settings.github_max_file_size_bytes
        )

        reason = None
        if language is None:
            reason = "Unsupported source-file extension"
        elif size > self.settings.github_max_file_size_bytes:
            reason = "File exceeds the configured size limit"

        return RepositoryFile(
            path=path,
            language=language,
            size_bytes=size,
            supported=supported,
            selected=supported,
            unsupported_reason=reason,
        )

    def _warnings(
        self,
        files: list[RepositoryFile],
        entries: list[Path],
    ) -> list[str]:
        warnings = []
        if len(entries) > self.settings.github_max_files:
            warnings.append(
                "Only the first "
                f"{self.settings.github_max_files} files are available for selection."
            )
        if not any(file.supported for file in files):
            warnings.append("No supported source files were found.")
        return warnings


# Keep the original construction name so existing imports remain stable.
GitHubMCPService = GitHubRepositoryService


def parse_github_repository_url(repository_url: str) -> GitHubRepository:
    parsed = urlparse(repository_url.strip())
    allowed_hosts = {"github.com", "www.github.com"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise InvalidRepositoryUrlError(
            "Repository URL must use HTTPS and point to github.com."
        )
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise InvalidRepositoryUrlError(
            "Repository URL cannot include credentials, query values, or fragments."
        )

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise InvalidRepositoryUrlError(
            "Repository URL must have the form https://github.com/owner/repository."
        )

    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name or owner.startswith("-") or name.startswith("-"):
        raise InvalidRepositoryUrlError("Repository owner and name are invalid.")
    return GitHubRepository(owner=owner, name=name)


def detect_source_technologies(
    checkout_path: Path,
    files: list[RepositoryFile],
) -> list[SourceTechnology]:
    languages: dict[str, list[str]] = {}
    for file in files:
        if file.language:
            languages.setdefault(file.language, []).append(file.path)

    technologies = [
        SourceTechnology(
            language=language,
            confidence=1.0,
            evidence=paths[:5],
        )
        for language, paths in sorted(languages.items())
    ]

    marker_evidence: dict[tuple[str, str], list[str]] = {}
    for file in files:
        if not file.supported:
            continue
        file_path = checkout_path / file.path
        try:
            content = file_path.read_text(encoding="utf-8")[:50_000].lower()
        except (OSError, UnicodeDecodeError):
            continue
        for marker, technology in FRAMEWORK_MARKERS.items():
            if marker in content:
                marker_evidence.setdefault(technology, []).append(file.path)

    for (language, framework), evidence in sorted(marker_evidence.items()):
        technologies.append(
            SourceTechnology(
                language=language,
                framework=framework,
                confidence=0.9,
                evidence=evidence[:5],
            )
        )
    return technologies


async def _git_output(checkout_path: Path, *arguments: str) -> str:
    process = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(checkout_path),
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise GitHubRepositoryError(
            stderr.decode("utf-8", errors="replace").strip()
            or "Could not inspect the cloned repository."
        )
    return stdout.decode("utf-8").strip()


def _validate_branch(branch: str | None) -> str | None:
    if branch is None or not branch.strip():
        return None
    normalized = branch.strip()
    if normalized.startswith("-") or not SAFE_BRANCH_PATTERN.fullmatch(normalized):
        raise GitHubRepositoryError("Branch name contains unsupported characters.")
    if ".." in normalized or normalized.endswith("/") or "//" in normalized:
        raise GitHubRepositoryError("Branch name is invalid.")
    return normalized


def _safe_relative_path(path: str) -> PurePosixPath:
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts or not normalized.parts:
        raise GitHubRepositoryError("Repository file path is unsafe.")
    return normalized


def _is_ignored_path(path: str) -> bool:
    return any(
        part.lower() in IGNORED_DIRECTORY_NAMES
        for part in PurePosixPath(path).parts
    )
