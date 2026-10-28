# Questionize — notes for coding agents

Chrome extension + web app that turns articles into verified GMAT/LSAT-style reasoning questions and keeps them in an open, community-improved question bank. Read `docs/ARCHITECTURE.md` before structural changes; it is the source of truth for the target design. `docs/KNOWLEDGE_MODEL.md` defines the knowledge model (blueprints, misconceptions, evidence) that questions are generated from.

## Stack

- `api/` — Rails 8 (PostgreSQL, Solid Queue/Cache/Cable, Minitest), deployed with Kamal 2
- `ai/` — FastAPI AI service, stateless, internal only
- `web/` — Vue 3 + TypeScript + Vite (Pinia, Vue Router)
- `extension/` — Chrome MV3; side panel moving to Vue 3 + TypeScript + Vite
- `packages/shared/` — shared TS types, API client, Vue components (pnpm workspace)

## Commands

```bash
# AI service
cd ai && pip install -r requirements-dev.txt && pytest
uvicorn questionize.app:app --reload --port 8000   # needs INTERNAL_TOKEN and a provider key in ai/.env

# Rails (needs PostgreSQL)
cd api && bin/setup && bin/rails test && bin/dev

# TS workspace (packages/shared, web; extension once migrated)
pnpm install && pnpm -r test && pnpm -r typecheck && pnpm --filter @questionize/web dev
```

## Rules

- **The repository is public.** Never commit secrets, server IPs, `.env` files, `.kamal/secrets` values or credentials. Put new configuration in `.env.example` with empty values.
- Rails owns all persistent state. The AI service never touches the database and is only called by Rails jobs with the `X-Internal-Token` header.
- Do not store article full text in permanent tables, and never store or publish uploaded contribution images (see ARCHITECTURE §5.5, §7).
- Knowledge extracted from sources holds abstract fields only: never a source's wording, stimulus, options or images (KNOWLEDGE_MODEL §1, §6).
- Shared bank items use adapted RC passages plus a source link, not long verbatim excerpts.
- Render model output as text (`textContent` / Vue interpolation), never as raw HTML.
- Hide an item's key, explanations and answer tallies until the requesting user has attempted it.
- Only a user's first attempt on an item is rated.
- Keep tests offline: scripted/mock models for the AI service, no live API calls in CI.
- Every commit should keep `pytest`, `bin/rails test` and `pnpm -r test` green for the parts that exist.

## Models

- The AI service defaults to the Meta Model API (`LLM_PROVIDER=meta`). Claude (`LLM_PROVIDER=anthropic`) remains available for development; the submitted demo must run on Meta models.

- Meta Model API (OpenAI-compatible, `https://api.meta.ai/v1`), default `muse-spark-1.3`; structured output via `response_format: {type: "json_schema", ...}` on Chat Completions.
- Muse Spark Open on Baseten: `meta-models/muse-spark-open-1026` (use this exact ID).
