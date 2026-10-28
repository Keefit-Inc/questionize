from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from conftest import ARTICLE, ScriptedLLM, make_analysis, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.pipeline import QuestionPipeline

TOKEN = "test-internal-token"
AUTH = {"X-Internal-Token": TOKEN}


def make_client(pipeline: QuestionPipeline | None = None, token: str = TOKEN) -> TestClient:
    p = ProviderConfig("meta", "http://x", "k", "m")
    pipeline = pipeline or QuestionPipeline(ScriptedLLM(), ScriptedLLM())
    return TestClient(create_app(Settings(primary=p, solver=p, internal_token=token), pipeline))


def test_generate_streams_ndjson_and_done():
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()], Question=[make_question("B")], CriticResult=[passing_critic()]
    )
    client = make_client(QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")])))

    r = client.post("/v1/generate", json={"text": ARTICLE, "types": ["CR"]}, headers=AUTH)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert events[-1]["stage"] == "done"
    assert events[-1]["result"]["questions"][0]["verification"]["verified"] is True


@pytest.mark.parametrize("headers", [{}, {"X-Internal-Token": "wrong"}, {"X-Internal-Token": ""}])
def test_generate_requires_internal_token(headers):
    r = make_client().post("/v1/generate", json={"text": ARTICLE}, headers=headers)
    assert r.status_code == 401


def test_unconfigured_token_refuses_everything():
    # An empty INTERNAL_TOKEN must not turn into "an empty header is accepted".
    r = make_client(token="").post("/v1/generate", json={"text": ARTICLE}, headers={"X-Internal-Token": ""})
    assert r.status_code == 401


def test_auth_is_checked_before_the_body():
    assert make_client().post("/v1/generate", json={"text": "too short"}).status_code == 401


def test_rejects_too_short_text():
    assert make_client().post("/v1/generate", json={"text": "too short"}, headers=AUTH).status_code == 422


def test_health_needs_no_token():
    body = make_client().get("/health").json()
    assert body["ok"] is True and body["model"] == "m"


def test_legacy_extension_routes_are_gone():
    assert make_client().post("/api/questions/stream", json={"text": ARTICLE}, headers=AUTH).status_code == 404


def test_declined_page_ends_the_stream_with_a_reason():
    declined = make_analysis().model_copy(
        update={"suitability": "not_an_article", "suitability_reason": "This is a shopping page."}
    )
    client = make_client(QuestionPipeline(ScriptedLLM(ArticleAnalysis=[declined]), ScriptedLLM()))
    r = client.post("/v1/generate", json={"text": ARTICLE}, headers=AUTH)
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert events[-1] == {"stage": "declined", "reason": "not_an_article", "message": "This is a shopping page."}
    assert "analyzed" not in [e["stage"] for e in events]
