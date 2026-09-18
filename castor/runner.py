"""Runs Agents on Questions, records each Forecast Run, and submits to Metaculus."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from castor.agents import Agent, AgentResult
from castor.clients.metaculus import MetaculusClient
from castor.config.settings import settings
from castor.models.forecast_summary import summarize_forecast
from castor.storage import RunRecord, get_engine, save_run
from castor.tracing import RunTrace, artifact, recording, step
from castor.utils.version import git_version

logger = logging.getLogger(__name__)


class ForecastRunner:
    """Forecasts Questions with one Agent and records every Forecast Run."""

    def __init__(
        self,
        metaculus_client: MetaculusClient,
        agent: Agent,
        record: bool = True,
        tournament: str | None = None,
    ):
        self.metaculus = metaculus_client
        self.agent = agent
        self.tournament = tournament
        self.engine = None
        if record and settings.database_url:
            self.engine = get_engine(settings.database_url)
        elif record:
            logger.warning("DATABASE_URL is not set; Forecast Runs will not be recorded")

    async def forecast_question(self, question_id: int, post_id: int, submit: bool) -> str:
        """Run the Agent on one Question and return a printable summary."""
        run_id = str(uuid.uuid4())
        trace = RunTrace()
        started_at = datetime.now(timezone.utc)
        question: dict[str, Any] | None = None
        result: AgentResult | None = None
        submitted = False
        error: str | None = None

        try:
            with recording(trace), step(
                "forecast-run", run_id=run_id, question_id=question_id, post_id=post_id
            ):
                with step("fetch-question"):
                    question = self.metaculus.get_post_details(post_id)["question"]
                    artifact("question", question)

                logger.info(f"Forecasting question {question_id}: {question['title']}")
                with step("agent", agent=self.agent.name):
                    artifact("agent_config", self.agent.config(), role="input")
                    result = await self.agent.forecast(question)
                    artifact("forecast", result.forecast)
                    artifact("comment", result.comment)
                logger.info(f"Generated forecast for question {question_id}: {result.forecast}")

                if submit:
                    with step("submit"):
                        payload = self.metaculus.create_forecast_payload(
                            result.forecast, question["type"]
                        )
                        artifact("payload", payload, role="input")
                        self.metaculus.post_forecast(question_id, payload)
                        submitted = True
                        self.metaculus.post_comment(post_id, result.comment)
                    logger.info(f"Posted forecast for question {question_id}")
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            if question is not None:
                self._save(run_id, trace, question, post_id, started_at, result, submitted, error)

        return _format_summary(question, post_id, result, submitted)

    async def forecast_questions(
        self, question_id_post_id: list[tuple[int, int]], submit: bool
    ) -> None:
        """Forecast Questions concurrently; raise if any of them failed."""
        logger.info(
            f"Starting forecasting for {len(question_id_post_id)} questions\n"
            f"  - Agent: {self.agent.name}\n"
            f"  - Submit predictions: {submit}"
        )

        with step("forecast-batch", tournament=self.tournament, agent=self.agent.name):
            forecast_summaries = await asyncio.gather(
                *[
                    self.forecast_question(question_id, post_id, submit)
                    for question_id, post_id in question_id_post_id
                ],
                return_exceptions=True,
            )

        print("\n", "#" * 100, "\nForecast Summaries\n", "#" * 100)

        errors = []
        for (question_id, post_id), forecast_summary in zip(
            question_id_post_id, forecast_summaries
        ):
            if isinstance(forecast_summary, Exception):
                error_msg = (
                    f"-----------------------------------------------\n"
                    f"Post {post_id} Question {question_id}:\n"
                    f"Error: {forecast_summary.__class__.__name__} {forecast_summary}\n"
                    f"URL: https://www.metaculus.com/questions/{post_id}/\n"
                )
                print(error_msg)
                logger.error(error_msg)
                errors.append(forecast_summary)
            else:
                print(forecast_summary)

        if errors:
            print("-----------------------------------------------\nErrors:\n")
            error_message = f"Errors were encountered: {errors}"
            print(error_message)
            logger.error(error_message)
            raise RuntimeError(error_message)

        logger.info(f"Completed forecasting for {len(question_id_post_id)} questions")

    def _save(
        self,
        run_id: str,
        trace: RunTrace,
        question: dict[str, Any],
        post_id: int,
        started_at: datetime,
        result: AgentResult | None,
        submitted: bool,
        error: str | None,
    ) -> None:
        if self.engine is None:
            return
        git_sha, git_dirty = git_version()
        try:
            save_run(
                self.engine,
                RunRecord(
                    id=run_id,
                    question=question,
                    post_id=post_id,
                    agent=self.agent.name,
                    agent_config=self.agent.config(),
                    git_sha=git_sha,
                    git_dirty=git_dirty,
                    environment=settings.castor_env,
                    tournament=self.tournament,
                    status="failed" if error else "succeeded",
                    error=error,
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                    forecast=result.forecast if result else None,
                    forecast_summary=_summarize(result, question),
                    submitted=submitted,
                    trace=trace,
                ),
            )
            logger.info(f"Recorded Forecast Run {run_id} for question {question['id']}")
        except Exception:
            # Recording must never change the outcome of a forecast
            logger.exception(f"Failed to record Forecast Run {run_id}")


def _summarize(result: AgentResult | None, question: dict[str, Any]) -> str | None:
    if result is None:
        return None
    try:
        return summarize_forecast(result.forecast, question)
    except Exception:
        logger.exception(f"Could not summarize forecast for question {question['id']}")
        return None


def _format_summary(
    question: dict[str, Any] | None,
    post_id: int,
    result: AgentResult | None,
    submitted: bool,
) -> str:
    assert question is not None and result is not None
    summary = f"-----------------------------------------------\nQuestion: {question['title']}\n"
    summary += f"URL: https://www.metaculus.com/questions/{post_id}/\n"
    if question["type"] == "multiple_choice":
        summary += f"options: {question['options']}\n"
    if question["type"] in ("numeric", "discrete"):
        summary += f"Forecast: {str(result.forecast)[:200]}...\n"
    else:
        summary += f"Forecast: {result.forecast}\n"
    summary += f"Comment:\n```\n{result.comment[:200]}...\n```\n\n"
    if submitted:
        summary += "Posted: Forecast was posted to Metaculus.\n"
    return summary
