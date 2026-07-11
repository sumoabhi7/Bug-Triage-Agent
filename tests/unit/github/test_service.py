from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from github import GithubException

from bta.domain import PRDraft, PRStatus
from bta.github.service import GitHubAdapter, GitHubAdapterError, GitHubAuthenticationError


def make_issue(number: int = 42, user: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=1000 + number,
        number=number,
        title="Crash when config key is missing",
        body="Traceback here",
        labels=[SimpleNamespace(name="bug"), SimpleNamespace(name="triage")],
        user=SimpleNamespace(login="octocat") if user is None else user,
        html_url=f"https://github.com/acme/widget/issues/{number}",
        state="open",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )


def test_authenticate_maps_current_user() -> None:
    client = Mock()
    client.get_user.return_value = SimpleNamespace(login="octocat")

    user = GitHubAdapter(client=client).authenticate()

    assert user.login == "octocat"


@pytest.mark.parametrize("login", [None, "", "   "])
def test_authenticate_rejects_missing_or_blank_login(login: str | None) -> None:
    client = Mock()
    client.get_user.return_value = SimpleNamespace(login=login)

    with pytest.raises(GitHubAuthenticationError) as raised:
        GitHubAdapter(client=client).authenticate()

    assert raised.value.__cause__ is not None


def test_get_issue_maps_github_issue_fields() -> None:
    repo = Mock()
    repo.get_issue.return_value = make_issue()
    client = Mock()
    client.get_repo.return_value = repo

    issue = GitHubAdapter(client=client).get_issue("acme/widget", 42)

    client.get_repo.assert_called_once_with("acme/widget")
    repo.get_issue.assert_called_once_with(number=42)
    assert issue.id == 1042
    assert issue.number == 42
    assert issue.title == "Crash when config key is missing"
    assert issue.body == "Traceback here"
    assert issue.labels == ["bug", "triage"]
    assert issue.author == "octocat"
    assert issue.url == "https://github.com/acme/widget/issues/42"
    assert issue.state == "open"
    assert issue.created_at.tzinfo is UTC


def test_get_issue_maps_missing_author_to_none_without_literal_none() -> None:
    repo = Mock()
    issue_data = make_issue(user=SimpleNamespace(login=None))
    delattr(issue_data, "user")
    repo.get_issue.return_value = issue_data
    client = Mock()
    client.get_repo.return_value = repo

    issue = GitHubAdapter(client=client).get_issue("acme/widget", 42)

    assert issue.author is None
    assert issue.author != "None"


@pytest.mark.parametrize("login", [None, "", "   "])
def test_get_issue_maps_missing_or_blank_author_login_to_none(login: str | None) -> None:
    repo = Mock()
    repo.get_issue.return_value = make_issue(user=SimpleNamespace(login=login))
    client = Mock()
    client.get_repo.return_value = repo

    issue = GitHubAdapter(client=client).get_issue("acme/widget", 42)

    assert issue.author is None
    assert issue.author != "None"


def test_list_open_issues_applies_labels_and_limit() -> None:
    repo = Mock()
    repo.get_issues.return_value = [make_issue(1), make_issue(2), make_issue(3)]
    client = Mock()
    client.get_repo.return_value = repo

    issues = GitHubAdapter(client=client).list_open_issues(
        "acme/widget",
        labels=["bug"],
        limit=2,
    )

    repo.get_issues.assert_called_once_with(state="open", labels=["bug"])
    assert [item.number for item in issues] == [1, 2]


def test_publish_draft_pull_request_maps_publication_fields() -> None:
    pull_request = Mock()
    pull_request.number = 99
    pull_request.html_url = "https://github.com/acme/widget/pull/99"
    repo = Mock()
    repo.create_pull.return_value = pull_request
    client = Mock()
    client.get_repo.return_value = repo
    draft = PRDraft(
        patch_draft_id=uuid4(),
        title="fix: handle missing config key",
        body="Draft body",
        base_branch="main",
        head_branch="bta/fix-42",
        labels=["bta-generated"],
    )

    published = GitHubAdapter(client=client).publish_draft_pull_request("acme/widget", draft)

    repo.create_pull.assert_called_once_with(
        title="fix: handle missing config key",
        body="Draft body",
        base="main",
        head="bta/fix-42",
        draft=True,
    )
    pull_request.add_to_labels.assert_called_once_with("bta-generated")
    assert published.github_pr_number == 99
    assert published.pr_url == "https://github.com/acme/widget/pull/99"
    assert published.status == PRStatus.PUBLISHED
    assert draft.status == PRStatus.PENDING


def test_github_api_failures_are_wrapped_with_original_cause() -> None:
    error = GithubException(status=500, data={"message": "boom"}, headers={})
    client = Mock()
    client.get_repo.side_effect = error

    with pytest.raises(GitHubAdapterError) as raised:
        GitHubAdapter(client=client).get_issue("acme/widget", 42)

    assert raised.value.__cause__ is error
