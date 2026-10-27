"""HTTP API used by the Chrome extension.

POST /api/questions          -> full JSON result when everything is done
POST /api/questions/stream   -> NDJSON stream of agent events, ending with {"stage": "done", ...}
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import __version__
from .config import Settings, load_settings
from .llm import LLMError, OpenAICompatLLM
from .pipeline import QuestionPipeline
from .schemas import GenerateRequest, GenerateResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("questionize")


def build_pipeline(settings: Settings) -> QuestionPipeline:
    primary = OpenAICompatLLM(settings.primary, timeout=settings.timeout_seconds)
    solver = (
        primary
        if settings.solver == settings.primary
        else OpenAICompatLLM(settings.solver, timeout=settings.timeout_seconds)
    )
    return QuestionPipeline(primary, solver, max_revisions=settings.max_revisions)


def create_app(settings: Settings | None = None, pipeline: QuestionPipeline | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Questionize", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    state: dict[str, QuestionPipeline | None] = {"pipeline": pipeline}

    def get_pipeline() -> QuestionPipeline:
        if state["pipeline"] is None:
            try:
                state["pipeline"] = build_pipeline(settings)
            except LLMError as e:
                raise HTTPException(status_code=503, detail=str(e)) from e
        return state["pipeline"]

    def clip(req: GenerateRequest) -> GenerateRequest:
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

    @app.post("/api/questions", response_model=GenerateResponse)
    async def generate(req: GenerateRequest) -> GenerateResponse:
        try:
            return await get_pipeline().run(clip(req))
        except LLMError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    @app.post("/api/questions/stream")
    async def generate_stream(req: GenerateRequest) -> StreamingResponse:
        pipeline = get_pipeline()
        req = clip(req)

        async def events() -> AsyncIterator[bytes]:
            queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

            async def emit(event: dict[str, Any]) -> None:
                await queue.put(event)

            async def worker() -> None:
                try:
                    result = await pipeline.run(req, emit)
                    await queue.put({"stage": "done", "result": result.model_dump()})
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

    return app


app = create_app()
