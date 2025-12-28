"""Forecast orchestrator that manages the entire forecasting process."""

from __future__ import annotations

import asyncio
import logging

from langfuse import get_client, observe

from castor.clients.llm import LLMClient
from castor.clients.metaculus import MetaculusClient
from castor.research import Researcher
from castor.forecasting.binary import BinaryForecaster
from castor.forecasting.multiple_choice import MultipleChoiceForecaster
from castor.forecasting.numeric import NumericForecaster

logger = logging.getLogger(__name__)


class Forecaster:
    """Forecasts a question."""

    def __init__(
        self,
        metaculus_client: MetaculusClient,
        llm_client: LLMClient,
        researcher: Researcher,
    ):
        """Initialize the forecast orchestrator.

        Args:
            metaculus_client: Client for Metaculus API.
            llm_client: Client for LLM calls.
            researcher: Researcher for research.
        """
        self.metaculus = metaculus_client
        self.binary_forecaster = BinaryForecaster(llm_client, researcher)
        self.numeric_forecaster = NumericForecaster(llm_client, researcher)
        self.multiple_choice_forecaster = MultipleChoiceForecaster(
            llm_client, researcher
        )

    @observe(as_type="span", name="forecast-question")
    async def forecast_individual_question(
        self,
        question_id: int,
        post_id: int,
        submit_prediction: bool,
        num_runs_per_question: int,
        skip_previously_forecasted_questions: bool,
    ) -> str:
        """Forecast a single question.

        Args:
            question_id: The question ID.
            post_id: The post ID.
            submit_prediction: Whether to submit the prediction to Metaculus.
            num_runs_per_question: Number of runs to perform per question.
            skip_previously_forecasted_questions: Whether to skip already forecasted questions.

        Returns:
            Summary string of the forecast.
        """
        post_details = self.metaculus.get_post_details(post_id)
        question_details = post_details["question"]
        title = question_details["title"]
        question_type = question_details["type"]

        # Update Langfuse span with metadata
        langfuse_context = get_client()
        langfuse_context.update_current_span(
            metadata={
                "question_type": question_type,
                "title": title[:100],
            }
        )

        summary_of_forecast = ""
        summary_of_forecast += (
            f"-----------------------------------------------\nQuestion: {title}\n"
        )
        summary_of_forecast += f"URL: https://www.metaculus.com/questions/{post_id}/\n"

        if question_type == "multiple_choice":
            options = question_details["options"]
            summary_of_forecast += f"options: {options}\n"

        if (
            self.metaculus.forecast_is_already_made(post_details)
            and skip_previously_forecasted_questions
        ):
            summary_of_forecast += "Skipped: Forecast already made\n"
            logger.info(f"Skipping question {question_id} - already forecasted")
            return summary_of_forecast

        logger.info(f"Forecasting question {question_id}: {title}")

        # Generate forecast based on question type
        if question_type == "binary":
            forecast, comment = await self.binary_forecaster.forecast(
                question_details, num_runs_per_question
            )
        elif question_type == "numeric":
            forecast, comment = await self.numeric_forecaster.forecast(
                question_details, num_runs_per_question
            )
        elif question_type == "discrete":
            forecast, comment = await self.numeric_forecaster.forecast(
                question_details, num_runs_per_question
            )
        elif question_type == "multiple_choice":
            forecast, comment = await self.multiple_choice_forecaster.forecast(
                question_details, num_runs_per_question
            )
        else:
            raise ValueError(f"Unknown question type: {question_type}")

        logger.info(f"Generated forecast for question {question_id}: {forecast}")

        if question_type == "numeric" or question_type == "discrete":
            summary_of_forecast += f"Forecast: {str(forecast)[:200]}...\n"
        else:
            summary_of_forecast += f"Forecast: {forecast}\n"

        summary_of_forecast += f"Comment:\n```\n{comment[:200]}...\n```\n\n"

        if submit_prediction:
            forecast_payload = self.metaculus.create_forecast_payload(
                forecast, question_type
            )
            self.metaculus.post_forecast(question_id, forecast_payload)
            self.metaculus.post_comment(post_id, comment)
            summary_of_forecast += "Posted: Forecast was posted to Metaculus.\n"
            logger.info(f"Posted forecast for question {question_id}")

        return summary_of_forecast

    @observe(as_type="span", name="forecast-batch")
    async def forecast_questions(
        self,
        open_question_id_post_id: list[tuple[int, int]],
        submit_prediction: bool,
        num_runs_per_question: int,
        skip_previously_forecasted_questions: bool,
    ) -> None:
        """Forecast multiple questions in parallel.

        Args:
            open_question_id_post_id: List of (question_id, post_id) tuples.
            submit_prediction: Whether to submit predictions to Metaculus.
            num_runs_per_question: Number of runs per question.
            skip_previously_forecasted_questions: Whether to skip already forecasted questions.
        """
        logger.info(f"Starting forecasting for {len(open_question_id_post_id)} questions")

        # Update Langfuse trace with metadata
        forecast_tasks = [
            self.forecast_individual_question(
                question_id=question_id,
                post_id=post_id,
                submit_prediction=submit_prediction,
                num_runs_per_question=num_runs_per_question,
                skip_previously_forecasted_questions=skip_previously_forecasted_questions,
            )
            for question_id, post_id in open_question_id_post_id
        ]
        forecast_summaries = await asyncio.gather(*forecast_tasks, return_exceptions=True)

        print("\n", "#" * 100, "\nForecast Summaries\n", "#" * 100)

        errors = []
        for question_id_post_id, forecast_summary in zip(
            open_question_id_post_id, forecast_summaries
        ):
            question_id, post_id = question_id_post_id
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

        logger.info(f"Completed forecasting for {len(open_question_id_post_id)} questions")
