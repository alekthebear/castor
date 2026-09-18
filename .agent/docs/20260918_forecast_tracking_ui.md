# Forecast Tracking UI

**Date**: September 18, 2026
**Status**: Designed, not started

Terms in **bold** are defined in [CONTEXT.md](CONTEXT.md). Deferred items live in [backlog.md](backlog.md).

## Goals

In priority order:

1. **Understanding**: trace and interpret how every Forecast was produced.
2. **Experiments**: deferred, but the data model must allow many **Forecast Runs** per **Question**, from different **Agents**, whether or not the Question has resolved.

The UI is private and runs locally for now; hosting comes later.

## Build order

The UI is the end product, so the data model is expected to shift as the UI is built.

1. **Record**: refactor today's pipeline into the `baseline` **Agent**, add one instrumentation layer that records **Steps**/**Artifacts** and also emits Langfuse spans, and write Forecast Runs to Supabase from both CI and local runs.
2. **Score**: add `castor sync` to pull resolutions and **Final Scores** and compute **Run Scores**.
3. **UI**: FastAPI backend + React (Vite) frontend with an overview page and a question detail page.

## Decisions

### Storage: self-contained records in Supabase Postgres

Each Forecast Run is stored in full (question snapshot, research, every **Sample**'s rationale, the Forecast, errors) in our own Postgres database on Supabase's free tier. Langfuse is linked only for token/cost/latency detail. Langfuse's free tier drops old traces, but Questions resolve months after they are forecast, which is exactly when the reasoning needs to be read. Supabase is accessed as plain Postgres (no Supabase-specific APIs) so the host can be swapped.

Rejected:
- **Langfuse as the database**: data retention, and no concept of Question or score.
- **Firestore**: the queries (runs per Question, filters, score aggregates) are relational.
- **Local SQLite**: production forecasts run in GitHub Actions, not on the machine running the UI.

### Recording

- Every Forecast Run is recorded, including Dev, unsubmitted, `--force`, and failed runs (with the error and partial Artifacts). Failures still alert via GitHub Actions.
- `--no-record` disables recording; recording is skipped with a warning when no database URL is configured.
- Runs are tagged with **Environment** (`CASTOR_ENV`, default `dev`; the scheduled job sets `prod`) and **Tournament**, for filtering in the UI.
- A run is buffered in memory and written once when it ends (in a `finally`, so failures are kept).
- Each run stores the question text it saw as an Artifact, in addition to the latest text on the Question.

### Agents

- Each Agent lives in `castor/agents/<name>/`; today's pipeline becomes `baseline`.
- Selected with `--agent <name>` (default `baseline`); the scheduled job reads it from a repo variable.
- A Forecast Run is identified by `(agent name, git SHA, Agent Config)`. No separate version numbers.
- Submission stays a per-invocation `--submit` flag, so a second Agent can shadow-run without submitting.
- `--num-runs` becomes `--num-samples` (old flag kept as a deprecated alias); the workflow's `NUM_RUNS` variable is updated.

### Scoring

- `castor sync` runs daily in CI over every Question with a Forecast Run that isn't finalized (resolved/annulled with a Final Score). It supports `--question` to force a refresh. The daily DB access also keeps the free Supabase project from pausing.
- **Final Score** comes from Metaculus (`my_forecasts.score_data`); spot peer score is shown on the overview.
- **Run Score** is the spot baseline score of one run's Forecast, computed with Metaculus's formula (`scoring/score_math.py` in the Metaculus repo). Binary/multiple choice: `100 · ln(p·N) / ln(N)`. Numeric/discrete: `50 · ln(pmf[bucket] / baseline)` from the 201-point CDF. No score for annulled/ambiguous Questions.
- The Community Prediction is not used: the API hides it from bot accounts, and the AIB rules don't permit another route.

### UI

- **Overview**: one row per Question, 2–3 lines tall: question snippet, type-aware Forecast summary (binary `73%`; multiple choice top options; numeric median with 80% interval and unit), spot peer score, Metaculus link. Summaries are computed when a run is recorded.
- **Detail**: the Question, every Forecast Run with its Step tree (timestamps and ordering preserved), and scores.
