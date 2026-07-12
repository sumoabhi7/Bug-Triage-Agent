from __future__ import annotations

from bta.services.exceptions import EvalServiceError
from bta.services.models import EvalRequest, EvalResult


class EvalService:
    async def run(self, request: EvalRequest) -> EvalResult:
        try:
            if request.benchmark_path is None:
                return EvalResult(message="evaluation benchmarks are not configured")
            return EvalResult(message=f"evaluation benchmarks pending: {request.benchmark_path}")
        except Exception as exc:
            raise EvalServiceError("evaluation failed") from exc
