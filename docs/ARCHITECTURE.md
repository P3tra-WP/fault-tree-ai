# Architecture

## Why a flat schema for the LLM, but a nested tree everywhere else

A fault tree is naturally recursive: a gate contains children, which may themselves be gates.
But neither OpenAI's nor Anthropic's *strict* structured-output/tool-calling modes support
recursive JSON Schema (a `$ref` that points back into an ancestor of itself). So the contract
handed to the LLM (`app/domain/models.py::LLMFaultTreeResponse`) is a **flat list of nodes**,
each with a `children_ids` array of string references, plus a `top_event_id` pointing at the
root. This is representable as a strict, non-recursive schema on both providers.

Once the LLM returns that flat list, `app/domain/tree_builder.py` walks it, checks for two things
a flat id-reference graph can have that a real tree cannot:

- **cycles** (a node ends up referencing an ancestor of itself), and
- **shared gates** (a gate id referenced as a child by more than one parent, which would make the
  structure a DAG rather than a tree).

only then does it build the real nested `FaultTree` (`app/domain/models.py::Gate` /
`BasicEvent`), which is what every other part of the system — the API responses, the cut-set and
probability math, the editor, the diagram — actually operates on. Basic events (leaves) *are*
allowed to repeat across branches (a shared root cause is legitimate in FTA); only gates must be
uniquely placed.

After the first LLM-generated draft, the LLM is never called again for that analysis. Every
subsequent operation — editing a node, adding a control, importing a previous tree, setting a
loss magnitude — is a pure, deterministic recomputation through `PUT /api/analyses/{id}` or
`POST /api/analyses/{id}/import`, handled entirely by `app/domain/*`.

## The "LLM drafts, code verifies" split

`app/llm/service.py::generate_fault_tree` is the only place that talks to a model. It:

1. Sends the system prompt (the FTA methodology, see `app/llm/prompts.py`) plus the user's threat
   model and Top Event, as a forced tool/function call against the flat schema (`strict: true`
   on both providers reduces malformed *syntax*).
2. Parses the raw JSON with `LLMFaultTreeResponse.model_validate_json` (Pydantic field-level and
   cross-field checks — malformed *semantics* like a gate with no children or a probability on a
   gate).
3. Builds the nested tree with `tree_builder.build_fault_tree` (graph-level checks: cycles, shared
   gates, unreachable nodes).
4. On any failure in steps 2–3, appends the concrete error message to the conversation and
   retries (capped at `MAX_LLM_ATTEMPTS`, default 3), giving the model a chance to self-correct
   against a specific, actionable error rather than a generic "try again."
5. If still invalid after all attempts, raises a clean error that the API surfaces as `422`.

## Deterministic math: cut sets and probability

`app/domain/cutsets.py::compute_minimal_cutsets` does a bottom-up Boolean expansion:

- a `BASIC` event contributes the singleton set `{its own id}`
- an `OR` gate's cut sets are the **union** of its children's cut sets (any one path suffices)
- an `AND` gate's cut sets are the **cartesian product** of its children's cut sets, each
  combination unioned together (every child's condition must hold simultaneously)

The raw result is then minimized by absorption (drop any set that is a superset of a smaller,
already-accepted set) to get the *minimal* cut sets — the smallest combinations of basic events
that are together sufficient to cause the Top Event.

`app/domain/probability.py::compute_probability` propagates leaf probabilities bottom-up the same
way (`OR` → `1 - Π(1-p)`, `AND` → `Π(p)`). This recursion is only *exact* if every basic event id
is unique across the whole tree — if the same id legitimately repeats in two branches (a shared
root cause), treating both branches as independent would double-count that cause. In that case
the code falls back to the standard FTA rare-event approximation over the minimal cut sets
instead (`P(top) ≈ Σ_cutsets Π(p_i)`), and reports `method: "approximate_rare_event"` so this is
visible rather than silently wrong. If any leaf is missing a probability, the whole computation
reports `method: "unavailable"` with a warning naming which basic events need estimates, rather
than guessing.

## Controls and the baseline/residual split

A `Control` (`app/domain/controls.py`) targets one basic event by id and carries an
`effectiveness` (0–1). `build_probability_lookups` produces two parallel probability lookups from
the same tree: `baseline` (each basic event's authored probability) and `residual` (the same,
multiplied by `Π(1 - effectiveness)` over every *active* control targeting that event). Both
lookups are run through the exact same cut-set/probability code, so every number in the API
response — the Top Event probability, every cut set's probability — has a baseline value and a
residual value side by side, without a second request round trip.

## Import and merge

`app/domain/merge.py::import_fault_tree` supports two modes:

- **replace**: the imported tree becomes the current tree outright.
- **merge**: every id in the imported tree is namespaced with a fresh `impN_` prefix (N increments
  per import on that analysis) to guarantee no collision
  with the current tree, then the imported root is appended as a new child of a gate the user
  picks in the current tree. Attaching under an `OR` gate is semantically clean (a new alternative
  path); attaching under an `AND` gate changes what that gate requires, which is allowed but
  surfaced as an explicit warning rather than silently changing the tree's meaning.

## Persistence

`storage/database_store.py` persists each complete `AnalysisResult` as JSON in SQL and also
materializes its computed minimal cut sets into `analysis_cut_sets`. This preserves the API's
recursive tree shape while making each prior analysis's cut sets available for later retrieval.
SQLite is the default (`DATABASE_URL=sqlite:///./data/fault-tree-ai.db`); a PostgreSQL URL can be
used without changing the storage contract. Docker Compose mounts `./data` so the default SQLite
database survives container replacement.

## Known v0 limitations

- **Tree, not DAG.** Gates can never be shared across branches (enforced at both the LLM-import
  path and the manual-edit path). This keeps the recursive math simple and correct but means you
  cannot express "this exact same sub-condition contributes to two different parents" for
  anything more complex than a repeated basic event.
- **Cut-set enumeration is capped.** Very wide `AND` fan-in can blow up combinatorially;
  `MAX_CUTSET_COMBINATIONS` (100,000) truncates with a warning rather than hanging.
- **ALE is a point estimate.** The FAIR-lite risk quantification is `probability × loss
  magnitude`, not a full Monte Carlo simulation over a min/likely/max loss distribution.
- **The interactive tree editor identifies rows by basic-event id.** If a tree has a basic-event
  id repeated across branches (legal in FTA), editing one occurrence in the visual editor may not
  cleanly distinguish it from the other — use the raw JSON editor for full control in that case.
