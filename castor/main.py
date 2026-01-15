"""Main entry point for Castor forecasting."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from langfuse import get_client, observe

from castor.clients import MetaculusClient
from castor.clients.llm import create_llm_client
from castor.config.settings import settings
from castor.forecasting import Forecaster
from castor.research import Researcher
from castor.utils import setup_logging
from castor.utils.telemetry import setup_otel_langfuse


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Castor - Automated forecasting bot for Metaculus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Question/Tournament selection (mutually exclusive)
    question_group = parser.add_mutually_exclusive_group()
    question_group.add_argument(
        "-p",
        "--post",
        type=int,
        help="Forecast a specific post ID (mutually exclusive with --tournament)",
    )
    question_group.add_argument(
        "-t",
        "--tournament",
        type=str,
        help="Forecast all questions in a tournament (ID or slug, mutually exclusive with --post)",
    )

    # Forecasting options
    parser.add_argument(
        "-s",
        "--submit",
        action="store_true",
        default=False,
        help="Submit predictions to Metaculus (default: False)",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Rerun forecast even if previously forecasted (default: False)",
    )
    parser.add_argument(
        "-n",
        "--num-runs",
        type=int,
        default=3,
        help="Number of runs per question (default: 3)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "gemini"],
        help="LLM provider (overrides LLM_PROVIDER env var)",
    )

    return parser.parse_args()


@observe(name="castor-run")
async def run_forecast(args: argparse.Namespace) -> None:
    """Main function to run the forecasting bot."""
    # Setup logging
    logger = setup_logging(log_level="INFO")
    logger.info("Starting Castor forecasting system")

    # Setup OpenTelemetry for non-OpenAI providers
    setup_otel_langfuse()

    # Initialize clients
    logger.info("Initializing clients...")
    metaculus_client = MetaculusClient()
    llm_client = create_llm_client(provider=args.provider)
    researcher = Researcher()
    forecaster = Forecaster(
        metaculus_client=metaculus_client,
        llm_client=llm_client,
        researcher=researcher,
    )

    # Get questions to forecast
    if args.post:
        post_id = args.post
        logger.info(f"Forecasting single question ID: {post_id}")
        post_details = metaculus_client.get_post_details(post_id)
        question_id = post_details["question"]["id"]
        questions_with_details = [(question_id, post_id, post_details)]
    elif args.tournament:
        logger.info(f"Fetching questions from tournament: {args.tournament}")
        open_questions = metaculus_client.get_open_questions_from_tournament(args.tournament)
        logger.info(f"Found {len(open_questions)} open questions")

        questions_with_details = []
        for question_id, post_id in open_questions:
            post_details = metaculus_client.get_post_details(post_id)
            question = post_details.get("question")
            if not question:
                continue
            questions_with_details.append((question_id, post_id, post_details))
    else:
        logger.error("Must specify either --post <post_id> or --tournament <tournament_id>")
        return

    # Filter out already forecasted questions
    open_question_id_post_id = []
    for question_id, post_id, details in questions_with_details:
        question = details.get("question")
        if not question:
            logger.warning(f"[Post {post_id}] Question {question_id} has no question data")
            continue
        logger.info(
            f"[Question {question_id}] {question['title']} "
            f"(Closes: {question['scheduled_close_time']})"
        )
        if not args.force and metaculus_client.forecast_is_already_made(details):
            logger.info(f"Skipping [Question {question_id}] - already forecasted")
            continue
        if not args.force and settings.forecast_window_before_close is not None:
            close_time = datetime.fromisoformat(question["scheduled_close_time"])
            hours_until_close = (close_time - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_until_close > settings.forecast_window_before_close:
                logger.info(
                    f"Skipping [Question {question_id}] - closes in {hours_until_close:.1f} hours "
                    f"(window: {settings.forecast_window_before_close}h)"
                )
                continue
        open_question_id_post_id.append((question_id, post_id))

    logger.info(f"Forecasting {len(open_question_id_post_id)} questions")

    # Determine settings from command-line args
    submit_prediction = args.submit
    num_runs_per_question = args.num_runs

    await forecaster.forecast_questions(
        open_question_id_post_id=open_question_id_post_id,
        submit_prediction=submit_prediction,
        num_runs_per_question=num_runs_per_question,
    )

    # Flush Langfuse traces
    if settings.langfuse_enabled:
        langfuse_client = get_client()
        trace_url = langfuse_client.get_trace_url()
        langfuse_client.flush()
        logger.info(f"Langfuse trace: {trace_url}")

    logger.info("Forecasting completed successfully")


def main() -> None:
    """Entry point for console script."""
    args = parse_args()
    asyncio.run(run_forecast(args))


if __name__ == "__main__":
    main()
