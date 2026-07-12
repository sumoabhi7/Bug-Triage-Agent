from __future__ import annotations

from bta.services.exceptions import DedupeServiceError
from bta.services.models import DedupeRequest, DedupeResult


class DedupeService:
    async def find_duplicates(self, request: DedupeRequest) -> DedupeResult:
        try:
            if request.evidence is not None:
                duplicates = list(request.evidence.duplicate_candidates)
            else:
                duplicates = list(request.case.candidate_duplicates)
            return DedupeResult(duplicates=duplicates)
        except Exception as exc:
            raise DedupeServiceError("duplicate detection failed") from exc
