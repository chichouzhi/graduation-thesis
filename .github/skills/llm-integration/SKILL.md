---
name: llm-integration
description: 'Integrate or switch AI/LLM providers for this project. Use for OpenAI-compatible providers, chat orchestration, topic keyword extraction, document pipelines, environment variables, and debugging AI call paths.'
argument-hint: 'provider name, env vars, or the feature you want to connect'
user-invocable: true
---

# LLM Integration Skill

Use this skill when you need to connect a real AI/LLM provider to the project, switch between mock and production providers, or trace where chat, topic keyword extraction, and document workflows call the model.

## When to Use
- Replace the default mock client with a real provider
- Add or adjust an OpenAI-compatible vendor
- Debug why chat, topic keywords, or document tasks are not reaching the model
- Update environment variables, Docker Compose, or deployment settings for AI access
- Keep model calls inside backend adapters, use cases, and workers

## Core Rule
Do not call the vendor API directly from the frontend or from Flask routes. Keep all AI calls behind:
- `app.adapter.llm`
- `app.use_cases.*`
- `app.task.*_jobs`

## Integration Flow
1. Identify the target provider.
   - For OpenAI-compatible vendors, reuse the existing HTTP adapter.
   - For non-compatible vendors, add a new adapter implementation first.
2. Configure runtime variables.
   - `LLM_PROVIDER`
   - `LLM_HTTP_BASE_URL`
   - `LLM_HTTP_MODEL`
   - `LLM_HTTP_API_KEY`
   - `LLM_HTTP_TIMEOUT_S`
3. Ensure the app bootstraps the client through `app.extensions.register_runtime_clients()`.
4. Keep feature logic in use cases:
   - Chat: `app/use_cases/chat_orchestration.py`
   - Topic keywords: `app/use_cases/topic_keywords.py`
   - Document pipeline: `app/use_cases/document_pipeline.py`
5. Keep worker jobs thin and asynchronous.
6. Update `docs/arch/llm_entrypoints.md` whenever a new LLM entrypoint is added or renamed.

## Provider Switching Checklist
- Mock for local development and tests
- OpenAI-compatible for most real providers
- Add a new provider branch in `app/adapter/llm/__init__.py` only when the vendor is not compatible
- Mirror any new env vars in `.env.example` and deployment config

## Recommended Validation
- Run targeted backend tests for chat, topic, and document paths
- Run the frontend build if the UI copy or state flow changed
- Start the full demo stack and confirm the smoke checks still pass

## Troubleshooting
- If the model is never called, check the worker path first
- If configuration is missing, verify `LLM_PROVIDER` and the HTTP variables in the runtime environment
- If a feature still uses the mock client, confirm the app registered the runtime client at startup
- If a new use case is added, make sure the entrypoint is documented in `docs/arch/llm_entrypoints.md`
