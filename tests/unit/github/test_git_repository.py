from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from git import Actor, Repo

from bta.github import service
from bta.github.service import GitHubAdapter, GitRepositoryError

AUTHOR = Actor("BTA Test", "bta@example.invalid")


def init_repo(path: Path) -> Repo:
    repo = Repo.init(path)
    (path / "README.md").write_text("# fixture\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit", author=AUTHOR, committer=AUTHOR)
    return repo


def test_clone_repository_accepts_local_path_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    init_repo(source)
    destination = tmp_path / "clone"

    checkout = GitHubAdapter(client=object()).clone_repository(source, destination)

    assert checkout.repo == str(source)
    assert checkout.path == destination.resolve()
    assert (destination / "README.md").read_text(encoding="utf-8") == "# fixture\n"
    assert checkout.default_branch in {"master", "main"}


def test_clone_repository_maps_github_slug_to_clone_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Path]] = []

    def clone_from(clone_url: str, destination: Path):
        calls.append((clone_url, destination))
        return SimpleNamespace(active_branch=SimpleNamespace(name="main"))

    monkeypatch.setattr(service.Repo, "clone_from", clone_from)

    checkout = GitHubAdapter(client=object()).clone_repository("acme/widget", tmp_path / "clone")

    assert calls == [("https://github.com/acme/widget.git", tmp_path / "clone")]
    assert checkout.repo == "acme/widget"
    assert checkout.default_branch == "main"


def test_create_and_checkout_branch(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo = init_repo(repo_path)
    adapter = GitHubAdapter(client=object())

    adapter.create_branch(repo_path, "bta/test")
    adapter.checkout_branch(repo_path, "bta/test")

    assert repo.active_branch.name == "bta/test"


def test_create_and_remove_worktree(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    init_repo(repo_path)
    worktree_path = tmp_path / "worktree"
    adapter = GitHubAdapter(client=object())

    ref = adapter.create_worktree(repo_path, worktree_path, "bta/worktree")

    assert ref.repo_path == repo_path.resolve()
    assert ref.worktree_path == worktree_path.resolve()
    assert ref.branch_name == "bta/worktree"
    assert (worktree_path / "README.md").exists()

    adapter.remove_worktree(repo_path, worktree_path, force=True)

    assert not worktree_path.exists()


def test_push_branch_to_local_bare_remote(tmp_path: Path) -> None:
    remote_path = tmp_path / "remote.git"
    Repo.init(remote_path, bare=True)
    repo_path = tmp_path / "repo"
    repo = init_repo(repo_path)
    repo.create_remote("origin", str(remote_path))
    adapter = GitHubAdapter(client=object())

    adapter.create_branch(repo_path, "bta/push")
    adapter.push_branch(repo_path, "bta/push")

    remote = Repo(remote_path)
    assert "bta/push" in [ref.name.removeprefix("origin/") for ref in remote.refs]


def test_repository_failures_are_wrapped_with_original_cause(tmp_path: Path) -> None:
    missing_repo = tmp_path / "missing"

    with pytest.raises(GitRepositoryError) as raised:
        GitHubAdapter(client=object()).checkout_branch(missing_repo, "main")

    assert raised.value.__cause__ is not None
