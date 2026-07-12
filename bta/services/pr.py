from __future__ import annotations

from bta.github.service import GitHubAdapter
from bta.services.exceptions import PublishServiceError
from bta.services.models import PublishRequest, PublishResult
from bta.services.unit_of_work import UnitOfWorkFactory


class PublishService:
    def __init__(
        self,
        *,
        github: GitHubAdapter,
        unit_of_work_factory: UnitOfWorkFactory,
    ) -> None:
        self._github = github
        self._unit_of_work_factory = unit_of_work_factory

    async def publish_draft_pr(self, request: PublishRequest) -> PublishResult:
        try:
            if not request.validation.overall_passed:
                raise PublishServiceError("cannot publish before validation succeeds")
            self._github.push_branch(request.repo_path, request.branch_name)
            published = self._github.publish_draft_pull_request(request.repo, request.pr_draft)
            if request.persist:
                async with self._unit_of_work_factory() as unit_of_work:
                    await unit_of_work.save_pr(request.case_id, published)
            return PublishResult(pr_draft=published)
        except PublishServiceError:
            raise
        except Exception as exc:
            raise PublishServiceError("draft PR publication failed") from exc
