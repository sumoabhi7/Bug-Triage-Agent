from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo
from github import Github, GithubException

from bta.domain import PRDraft, PRStatus


@dataclass(frozen=True, slots=True)
class GitHubUser:
    login: str


@dataclass(frozen=True, slots=True)
class GitHubIssue:
    id: int
    number: int
    title: str
    body: str
    labels: list[str]
    author: str | None
    url: str | None
    state: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RepositoryCheckout:
    repo: str
    path: Path
    default_branch: str


@dataclass(frozen=True, slots=True)
class WorktreeRef:
    repo_path: Path
    worktree_path: Path
    branch_name: str
    base_ref: str


class GitHubAdapterError(RuntimeError):
    """Base error for GitHub adapter failures."""


class GitHubAuthenticationError(GitHubAdapterError):
    """Raised when GitHub authentication fails."""


class GitRepositoryError(GitHubAdapterError):
    """Raised when local git operations fail."""


class GitHubAdapter:
    """Infrastructure adapter for GitHub API and local git operations."""

    def __init__(
        self,
        *,
        token: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._client = client if client is not None else Github(token)

    def authenticate(self) -> GitHubUser:
        try:
            user = self._client.get_user()
            login = _optional_string(getattr(user, "login", None))
            if login is None:
                raise ValueError("authenticated GitHub user login is missing")
            return GitHubUser(login=login)
        except _GITHUB_FAILURES as error:
            raise GitHubAuthenticationError("GitHub authentication failed") from error

    def get_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        try:
            github_repo = self._client.get_repo(repo)
            issue = github_repo.get_issue(number=issue_number)
            return self._map_issue(issue)
        except _GITHUB_FAILURES as error:
            raise GitHubAdapterError(f"failed to fetch issue {repo}#{issue_number}") from error

    def list_open_issues(
        self,
        repo: str,
        *,
        labels: Sequence[str] = (),
        limit: int | None = None,
    ) -> list[GitHubIssue]:
        try:
            github_repo = self._client.get_repo(repo)
            if labels:
                issues = github_repo.get_issues(state="open", labels=list(labels))
            else:
                issues = github_repo.get_issues(state="open")
            mapped: list[GitHubIssue] = []
            for issue in issues:
                mapped.append(self._map_issue(issue))
                if limit is not None and len(mapped) >= limit:
                    break
            return mapped
        except _GITHUB_FAILURES as error:
            raise GitHubAdapterError(f"failed to list issues for {repo}") from error

    def clone_repository(
        self,
        repo: str | Path,
        destination: Path,
        *,
        branch: str | None = None,
    ) -> RepositoryCheckout:
        try:
            clone_url = self._clone_source(repo)
            if branch is None:
                cloned = Repo.clone_from(clone_url, destination)
            else:
                cloned = Repo.clone_from(clone_url, destination, branch=branch)
            default_branch = self._active_branch_name(cloned)
            return RepositoryCheckout(
                repo=str(repo),
                path=destination.resolve(),
                default_branch=default_branch,
            )
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to clone repository {repo}") from error

    def create_branch(
        self,
        repo_path: Path,
        branch_name: str,
        *,
        start_point: str = "HEAD",
    ) -> None:
        try:
            repo = Repo(repo_path)
            repo.create_head(branch_name, repo.commit(start_point))
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to create branch {branch_name}") from error

    def checkout_branch(self, repo_path: Path, branch_name: str) -> None:
        try:
            repo = Repo(repo_path)
            repo.git.checkout(branch_name)
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to checkout branch {branch_name}") from error

    def create_worktree(
        self,
        repo_path: Path,
        worktree_path: Path,
        branch_name: str,
        *,
        base_ref: str = "HEAD",
    ) -> WorktreeRef:
        try:
            repo = Repo(repo_path)
            repo.git.worktree("add", "-b", branch_name, str(worktree_path), base_ref)
            return WorktreeRef(
                repo_path=repo_path.resolve(),
                worktree_path=worktree_path.resolve(),
                branch_name=branch_name,
                base_ref=base_ref,
            )
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to create worktree {worktree_path}") from error

    def remove_worktree(
        self,
        repo_path: Path,
        worktree_path: Path,
        *,
        force: bool = False,
    ) -> None:
        try:
            repo = Repo(repo_path)
            arguments = ["remove"]
            if force:
                arguments.append("--force")
            arguments.append(str(worktree_path))
            repo.git.worktree(*arguments)
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to remove worktree {worktree_path}") from error

    def push_branch(
        self,
        repo_path: Path,
        branch_name: str,
        *,
        remote: str = "origin",
    ) -> None:
        try:
            repo = Repo(repo_path)
            repo.remote(remote).push(f"{branch_name}:{branch_name}")
        except _GIT_FAILURES as error:
            raise GitRepositoryError(f"failed to push branch {branch_name}") from error

    def publish_draft_pull_request(self, repo: str, draft: PRDraft) -> PRDraft:
        try:
            github_repo = self._client.get_repo(repo)
            pull_request = github_repo.create_pull(
                title=draft.title,
                body=draft.body,
                base=draft.base_branch,
                head=draft.head_branch,
                draft=True,
            )
            if draft.labels and hasattr(pull_request, "add_to_labels"):
                pull_request.add_to_labels(*draft.labels)
            return draft.model_copy(
                update={
                    "github_pr_number": int(pull_request.number),
                    "pr_url": str(pull_request.html_url),
                    "status": PRStatus.PUBLISHED,
                }
            )
        except _GITHUB_FAILURES as error:
            raise GitHubAdapterError(f"failed to publish draft pull request for {repo}") from error

    @staticmethod
    def _map_issue(issue: Any) -> GitHubIssue:
        labels = [str(label.name) for label in getattr(issue, "labels", [])]
        author = _optional_string(getattr(getattr(issue, "user", None), "login", None))
        return GitHubIssue(
            id=int(issue.id),
            number=int(issue.number),
            title=str(issue.title),
            body=str(issue.body or ""),
            labels=labels,
            author=author,
            url=str(issue.html_url) if getattr(issue, "html_url", None) else None,
            state=str(issue.state),
            created_at=_ensure_utc(issue.created_at),
            updated_at=_ensure_utc(issue.updated_at),
        )

    @staticmethod
    def _clone_source(repo: str | Path) -> str:
        if isinstance(repo, Path):
            return str(repo)
        if _is_git_url(repo):
            return repo
        if _is_github_slug(repo):
            return f"https://github.com/{repo}.git"
        return repo

    @staticmethod
    def _active_branch_name(repo: Repo) -> str:
        try:
            return str(repo.active_branch.name)
        except TypeError:
            return "HEAD"


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "None":
        return None
    return text


def _is_git_url(value: str) -> bool:
    return (
        "://" in value
        or value.startswith("git@")
        or value.startswith("ssh://")
        or value.startswith("file://")
        or value.endswith(".git")
    )


def _is_github_slug(value: str) -> bool:
    owner_repo = value.split("/")
    return len(owner_repo) == 2 and all(part.strip() for part in owner_repo)


_GITHUB_FAILURES = (GithubException, OSError, AttributeError, TypeError, ValueError)
_GIT_FAILURES = (
    GitCommandError,
    InvalidGitRepositoryError,
    NoSuchPathError,
    OSError,
    ValueError,
)
