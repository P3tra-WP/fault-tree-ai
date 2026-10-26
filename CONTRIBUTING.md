# Contributing

## Dev setup

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # Vite dev server on :5173, proxies /api to :8000
```

Running both separately (rather than `docker compose up`) is the dev-with-hot-reload workflow.
Set `CORS_ORIGINS=http://localhost:5173` in `backend/.env` for this to work.

## Tests

```bash
cd backend && pytest
cd frontend && npm run build   # type-checks + verifies the production build
```

## Style

- Python: no enforced formatter yet -- `ruff`/`black` with default settings are welcome
  additions if you want to add the config.
- TypeScript: standard `tsc` strict mode (see `frontend/tsconfig.json`) is the only enforced
  check today; an ESLint/Prettier setup is a good first PR if you'd like to add one.

## Pull requests

- Keep PRs focused on one change. Add/update tests for anything under `backend/app/domain/` —
  that's the deterministic math (cut sets, probability, controls, risk) and it should stay
  fully covered.
- No live calls to OpenAI/Anthropic in tests — stub the `LLMProvider` interface
  (see `backend/tests/test_api_analyses.py` for the pattern).
