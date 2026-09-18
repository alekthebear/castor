# Castor

An automated forecasting system for Metaculus. This context covers producing forecasts and tracking them so their reasoning and performance can be understood.

## Language

### Metaculus

**Question**:
A single Metaculus question with one resolvable outcome (binary, numeric, discrete, or multiple choice).
_Avoid_: Post (a Post is the Metaculus page that contains a Question)

**Tournament**:
A Metaculus collection of Questions that are forecast and scored as a group.

**Account**:
The single Metaculus bot account under which all Submitted Forecasts are made, whichever Agent produced them.
_Avoid_: Bot

### Forecasting

**Castor**:
The whole system: Agents, the CLI, scheduled jobs, storage, and UI.
_Avoid_: The bot

**Agent**:
A named process that takes a Question and produces a Forecast, leaving a trace of Steps and Artifacts along the way. It may be a fixed workflow or an agentic loop.
_Avoid_: Bot, workflow, forecaster, pipeline

**Agent Config**:
The settings that shape an Agent's behavior beyond its code, such as provider, model, Sample count, and research provider.
_Avoid_: Workflow Config

**Forecast Run**:
One execution of an Agent against one Question at a point in time, tied to a code version (git SHA) and an Agent Config. A Question can have many Forecast Runs, whether or not it has resolved.
_Avoid_: Answer, run, attempt

**Step**:
A timed unit of work within a Forecast Run, such as research, one LLM call, or aggregation. Steps nest, forming a tree ordered by when they happened.
_Avoid_: Stage, span

**Artifact**:
A piece of content a Step consumes or produces, such as the question snapshot, a prompt, a research report, a rationale, or an error.

**Sample**:
One independent LLM rationale and the value extracted from it, for Agents that aggregate several attempts into a Forecast.
_Avoid_: Run

**Forecast**:
The final probability or distribution a Forecast Run produces.
_Avoid_: Answer, prediction

**Submitted Forecast**:
A Forecast that was posted to Metaculus. Only Submitted Forecasts count toward the Final Score.

**Environment**:
Where a Forecast Run was produced: Prod (the scheduled job) or Dev (manual or local runs). Used to filter, never to change behavior.

### Scoring

**Final Score**:
The scores Metaculus assigns the Account on a Question after it resolves, summarizing all Submitted Forecasts on it. Spot peer score is the headline number.
_Avoid_: Question Score

**Run Score**:
A score Castor computes for one Forecast Run once its Question resolves, as if that Forecast alone had been standing at scoring time. Works for unsubmitted runs too.
