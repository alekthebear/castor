"""Main entry point for Castor forecasting."""

from __future__ import annotations

import argparse
import asyncio

from langfuse import Langfuse

from castor.clients import LLMClient, MetaculusClient
from castor.research import Researcher
from castor.config.settings import settings
from castor.forecasting import Forecaster
from castor.utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Castor - Automated forecasting bot for Metaculus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Question/Tournament selection (mutually exclusive)
    question_group = parser.add_mutually_exclusive_group()
    question_group.add_argument(
        "-q",
        "--question",
        type=int,
        help="Forecast a specific question ID (mutually exclusive with --tournament)",
    )
    question_group.add_argument(
        "-t",
        "--tournament",
        type=str,
        help="Forecast all questions in a tournament (ID or slug, mutually exclusive with --question)",
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
        help="Rerun forecast even if previously forecasted (default: False, skip previously forecasted)",
    )
    parser.add_argument(
        "-n",
        "--num-runs",
        type=int,
        default=3,
        help="Number of runs per question (default: 5)",
    )

    return parser.parse_args()


async def run_forecast(args: argparse.Namespace) -> None:
    """Main function to run the forecasting bot."""
    # Setup logging
    logger = setup_logging(log_level="INFO")
    logger.info("Starting Castor forecasting system")

    # Initialize clients
    logger.info("Initializing clients...")
    metaculus_client = MetaculusClient()
    llm_client = LLMClient()
    researcher = Researcher()

    # Initialize forecast orchestrator
    forecaster = Forecaster(
        metaculus_client=metaculus_client,
        llm_client=llm_client,
        researcher=researcher,
    )

    # Get questions to forecast
    if args.question:
        # Single question mode - args.question is the post_id from the URL
        post_id = args.question
        logger.info(f"Forecasting single question ID: {post_id}")
        # Fetch post details to get the actual question_id
        post_details = metaculus_client.get_post_details(post_id)
        question_id = post_details["question"]["id"]
        open_question_id_post_id = [(question_id, post_id)]
    elif args.tournament:
        # Tournament mode
        logger.info(f"Fetching questions from tournament: {args.tournament}")
        open_question_id_post_id = metaculus_client.get_open_questions_from_tournament(
            args.tournament
        )
        logger.info(f"Found {len(open_question_id_post_id)} open questions")

        # Print question details
        for question_id, post_id in open_question_id_post_id:
            post_details = metaculus_client.get_post_details(post_id)
            question = post_details.get("question")
            if question:
                logger.info(
                    f"ID: {question['id']}\n"
                    f"Q: {question['title']}\n"
                    f"Closes: {question['scheduled_close_time']}"
                )
    else:
        # No command-line args provided - error
        logger.error("Must specify either --question <question_id> or --tournament <tournament_id>")
        return

    # Determine settings from command-line args
    submit_prediction = args.submit
    num_runs_per_question = args.num_runs
    skip_previously_forecasted = not args.force

    # Run forecasting
    logger.info(
        f"Starting forecasting with the following settings:\n"
        f"  - Submit predictions: {submit_prediction}\n"
        f"  - Runs per question: {num_runs_per_question}\n"
        f"  - Skip previously forecasted: {skip_previously_forecasted}"
    )

    await forecaster.forecast_questions(
        open_question_id_post_id=open_question_id_post_id,
        submit_prediction=submit_prediction,
        num_runs_per_question=num_runs_per_question,
        skip_previously_forecasted_questions=skip_previously_forecasted,
    )

    # Flush Langfuse traces
    if settings.langfuse_enabled:
        langfuse = Langfuse(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_base_url,
        )
        langfuse.flush()
        logger.info("Flushed Langfuse traces")

    logger.info("Forecasting completed successfully")


def main() -> None:
    """Entry point for console script."""
    args = parse_args()
    asyncio.run(run_forecast(args))


if __name__ == "__main__":
    main()
