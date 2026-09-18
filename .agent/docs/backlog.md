# Backlog

Deferred ideas from design sessions (see [20260918_forecast_tracking_ui.md](20260918_forecast_tracking_ui.md)).

- **Backfill past Submitted Forecasts**: import forecasts already on Metaculus (value, comment, score) as imported Forecast Runs without Samples or research.
- **Stage-level replay**: persist artifacts per stage so a new Forecast Run can reuse an earlier run's artifacts (e.g. same research, different prompt).
- **Experiments**: compare Agents/Agent Configs on the same Questions, beyond per-run Run Scores.
- **Hosting**: move the UI from a local service to a hosted one.
- **Compare Postgres hosts**: evaluate Supabase vs alternatives (Neon, Turso/libSQL, self-hosted) on free-tier limits, inactivity pausing, and backups.
- **Question revisions in the UI**: decide how to show that a Forecast Run saw an older question text than the current one.
- **Crowd comparison**: Metaculus hides the Community Prediction from bot accounts via the API, and the AIB rules don't allow reading it another way. Revisit if Metaculus publishes it (e.g. post-tournament datasets).
- **Overview row design**: 2–3 lines per Question row; richer Forecast summaries (top 2–3 options, interval + unit) sized to the column.
- **Artifact lineage**: record which Artifacts a Step's outputs were derived from (needed for stage replay).
- **AIB human-in-the-loop rule**: the rules forbid modifying a bot based on its output on open competition questions; consider a UI warning on open Tournament Questions.
- **Detailed data model**: Step/Artifact schema, instrumentation API shape, and how the Langfuse sink attaches.
- **Detail page design**: Final Score breakdown (peer/baseline, spot vs time-averaged), Run Scores per run, question revisions.
- **Streaming Step writes**: write Steps as they happen, for a live view and resilience to killed runners.
