# fault-tree-ai

An open-source tool that uses an LLM (your own OpenAI, Anthropic, or Google Gemini key) to draft a **Fault Tree
Analysis (FTA)** from a threat model, then lets you edit it, add controls, import a previous
analysis, and quantify the risk in dollars — all computed deterministically in code, not by the
model.

## What is Fault Tree Analysis

FTA is a safety-engineering technique (Bell Labs, 1960s; standard in aerospace and nuclear
safety) for reasoning about a single unacceptable outcome — the **Top Event** — by working
backwards through logic gates to the specific, combinable conditions that would cause it:

- **OR gate** — any one child condition is enough on its own.
- **AND gate** — every child condition has to hold at the same time.
- **Basic event** — a leaf condition, optionally with a rough probability.

From a tree built this way you can compute **minimal cut sets** (the smallest combinations of
basic events that together cause the Top Event — i.e. exactly which handful of things to test or
control first) and, where you have leaf probabilities, propagate a Top Event probability instead
of arguing about "medium" on a risk matrix.

Threat modeling and attack trees tell you the routes to a bad outcome; FTA tells you which of
those routes to close first, and lets you prove you've closed them.

## Features

- **LLM-drafted fault trees.** Upload a threat model or system document (Markdown, JSON, or Mermaid
  source) and state a Top Event; the app
  asks your chosen LLM to draft the OR/AND gate structure and basic events. The LLM only ever
  drafts the structure — cut sets and probabilities are always computed by deterministic code,
  never by the model.
- **Full structural editor.** Drag to reparent or reorder nodes, edit descriptions and
  probabilities inline, toggle a gate between AND/OR, add or delete nodes — or drop into a raw
  JSON view for full control.
- **Controls with before/after impact.** Attach a mitigation to any basic event with an
  effectiveness percentage, and see the Top Event probability and every cut set recompute with
  baseline vs. residual (with-controls) numbers side by side.
- **Import a previous analysis.** Bring in a prior FTA JSON export and either replace the current
  tree or merge it in as a new subtree under a gate you pick.
- **FAIR-lite risk quantification.** Enter a loss magnitude for the Top Event and get an
  Annualized Loss Expectancy (probability × loss) for baseline and residual, so a control's value
  shows up as a dollar figure, not just a percentage.
- **BYOK, session-only.** Your OpenAI, Anthropic, or Google Gemini API key is entered in the UI, used only for that
  session's requests, and never written to disk or logged by the backend.
- **Export.** JSON or a human-readable Markdown report.

## Quick start

```bash
git clone <this repo>
cd fault-tree-ai
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:8000`. Upload `examples/hal9000-threat-model.md`, give it a Top Event
(e.g. *"Agent takes an irreversible, life-threatening action against crew members"*), pick a
provider, and paste in your API key.

Want to skip generation entirely? On the same screen, import `examples/hal9000-fta.json` — a
previously-generated FTA export — to jump straight into the editor.

## Local development

See [CONTRIBUTING.md](CONTRIBUTING.md) for running the backend and frontend separately with hot
reload instead of the Docker path.

## How it works

1. You upload a threat model and state a Top Event.
2. The backend asks your chosen LLM to draft the fault tree as a flat, strict-schema-compatible
   node list (neither provider's strict structured output supports the recursive shape a fault
   tree actually has), then validates and reconstructs it into a real nested tree — retrying the
   model with the specific validation error if it gets the structure wrong.
3. From there, every edit, control toggle, import, or loss-magnitude change is pure deterministic
   computation (no further LLM calls): minimal cut sets via Boolean expansion, Top Event
   probability via bottom-up propagation, both a baseline and a "with active controls" residual
   view.
4. You edit, add controls, quantify risk, and export.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the details, including how repeated basic
events and import merges are handled.

## API keys & privacy

Your API key is entered in the UI and sent with each request to the backend, which forwards it
directly to your chosen provider for that call only. It is never written to disk, never logged,
and not required for anything except the initial generation step — editing, controls, import, and
risk quantification never touch the LLM at all.

## Configuration

See [`.env.example`](.env.example). None of the settings there are LLM API keys — those are
always BYOK via the UI, per session.

## API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | liveness check |
| `POST` | `/api/analyses` | generate a new fault tree via an LLM |
| `POST` | `/api/analyses/import` | create a new analysis from an imported FTA JSON, no LLM |
| `GET` | `/api/analyses/{id}` | fetch current state |
| `PUT` | `/api/analyses/{id}` | recompute after an edit, control change, or loss-magnitude entry |
| `POST` | `/api/analyses/{id}/import` | replace or merge an imported tree into an existing analysis |
| `GET` | `/api/analyses/{id}/export?format=json\|markdown` | export |

## Known v0 limitations

- Analyses and computed minimal cut sets are stored in SQLite by default. Configure
  `DATABASE_URL` for another SQL database such as PostgreSQL.
- A fault tree must stay a tree: a gate can't be shared by two parents (a DAG). A basic event id
  *can* legitimately repeat across branches (a shared root cause) — but the visual tree editor
  identifies rows by that id, so editing one occurrence may not cleanly distinguish it from
  another with the same id. Use the raw JSON editor for full control there.
- Very wide `AND` fan-in is capped during cut-set enumeration (100,000 combinations) to avoid
  combinatorial blowup; beyond that it truncates with a warning rather than hanging.
- Risk quantification is a point estimate (probability × loss magnitude), not a full Monte Carlo
  simulation over a loss distribution.
- No authentication — this is a local, single-user tool.

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap / good first issues

- Full FAIR Monte Carlo mode (min/likely/max loss magnitude → a loss-exceedance curve).
- ESLint/Prettier setup for the frontend; ruff/black for the backend.
- Code-split the Mermaid bundle (it currently pulls in every diagram type Mermaid supports).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
