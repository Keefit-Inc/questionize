"""Internal HTTP API, called only by Rails jobs.

GET  /health        -> liveness and configured models (no auth)
POST /v1/judge      -> Argument Judge measurements for an argument and its options
POST /v1/map        -> NDJSON stream ending with {"stage": "map", "map": {...}} then {"stage": "done"}
POST /v1/generate   -> NDJSON stream of agent events, ending with {"stage": "done", ...},
                       {"stage": "declined", ...} for an unsuitable page, or {"stage": "failed", ...}

Every /v1 request must carry the shared secret in the X-Internal-Token header.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from . import __version__
from .config import Settings, load_settings
from .llm import LLMError, make_llm
from .judge import ArgumentJudge
from .mapper import MapPipeline
from .pipeline import ArticleDeclined, QuestionPipeline
from .schemas import GenerateRequest, JudgeRequest, JudgeResult, MapRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("questionize")


def build_pipeline(settings: Settings) -> QuestionPipeline:
    primary = make_llm(settings.primary, timeout=settings.timeout_seconds)
    solver = primary if settings.solver == settings.primary else make_llm(settings.solver, timeout=settings.timeout_seconds)
    return QuestionPipeline(
        primary,
        solver,
        max_revisions=settings.max_revisions,
        max_copied_words=settings.max_copied_words,
        judge=build_judge(settings, primary, solver) if settings.judge_enabled else None,
    )


def build_judge(settings: Settings, primary, solver) -> ArgumentJudge:
    # The solver model doubles as the second, independent judge.
    return ArgumentJudge(
        [primary, solver],
        samples_per_judge=settings.judge_samples,
        min_first_rate=settings.judge_min_first_rate,
        min_margin=settings.judge_min_margin,
    )


def create_app(settings: Settings | None = None, pipeline: QuestionPipeline | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Questionize AI", version=__version__)

    def require_internal_token(x_internal_token: str = Header("")) -> None:
        expected = settings.internal_token
        if not expected or not secrets.compare_digest(x_internal_token.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Token")

    v1 = APIRouter(prefix="/v1", dependencies=[Depends(require_internal_token)])

    state: dict[str, QuestionPipeline | None] = {"pipeline": pipeline}

    def get_pipeline() -> QuestionPipeline:
        if state["pipeline"] is None:
            try:
                state["pipeline"] = build_pipeline(settings)
            except LLMError as e:
                raise HTTPException(status_code=503, detail=str(e)) from e
        return state["pipeline"]

    def clip(req):
        if len(req.text) > settings.max_article_chars:
            req = req.model_copy(update={"text": req.text[: settings.max_article_chars]})
        return req

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "model": settings.primary.model,
            "solver_model": settings.solver.model,
        }

    @v1.post("/judge", response_model=JudgeResult)
    async def judge(req: JudgeRequest) -> JudgeResult:
        pipeline = get_pipeline()
        if pipeline.judge is None:
            raise HTTPException(status_code=503, detail="Argument Judge is disabled (JUDGE_ENABLED=false)")
        try:
            return await pipeline.judge.judge(req)
        except LLMError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

    @v1.post("/generate")
    async def generate(req: GenerateRequest) -> StreamingResponse:
        pipeline = get_pipeline()
        req = clip(req)

        async def run(emit) -> list[dict[str, Any]]:
            result = await pipeline.run(req, emit)
            return [{"stage": "done", "result": result.model_dump()}]

        return stream(run)

    @v1.post("/map")
    async def map_argument(req: MapRequest) -> StreamingResponse:
        pipeline = get_pipeline()
        if pipeline.judge is None:
            raise HTTPException(status_code=503, detail="Argument Judge is disabled (JUDGE_ENABLED=false)")
        mapper = MapPipeline(pipeline.primary, pipeline.judge)
        req = clip(req)

        async def run(emit) -> list[dict[str, Any]]:
            argument_map = await mapper.run(req, emit)
            return [{"stage": "map", "map": argument_map.model_dump()}, {"stage": "done"}]

        return stream(run)

    app.include_router(v1)
    return app


def stream(run) -> StreamingResponse:
    """Runs `run(emit)` and streams its progress events, then its final events, as NDJSON."""

    async def events() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def emit(event: dict[str, Any]) -> None:
            await queue.put(event)

        async def worker() -> None:
            try:
                for event in await run(emit):
                    await queue.put(event)
            except ArticleDeclined as e:
                await queue.put({"stage": "declined", "reason": e.reason, "message": e.message})
            except Exception as e:  # surfaced to the client as a final event
                log.exception("pipeline failed")
                await queue.put({"stage": "failed", "message": str(e)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(worker())
        try:
            while (event := await queue.get()) is not None:
                yield (json.dumps(event) + "\n").encode()
        finally:
            task.cancel()

    return StreamingResponse(events(), media_type="application/x-ndjson")


app = create_app()
