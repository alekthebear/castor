"""Main entry point for BearBot forecasting."""

from __future__ import annotations

import argparse
import asyncio

import dotenv

from bearbot.clients import LLMClient, MetaculusClient, ResearchOrchestrator
from bearbot.forecasting import ForecastOrchestrator
from bearbot.utils import setup_logging

# Load environment variables
dotenv.load_dotenv()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="BearBot - Automated forecasting bot for Metaculus",
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


async def main(args: argparse.Namespace) -> None:
    """Main function to run the forecasting bot."""
    # Setup logging
    logger = setup_logging(log_level="INFO")
    logger.info("Starting BearBot forecasting system")

    # Initialize clients
    logger.info("Initializing clients...")
    metaculus_client = MetaculusClient()
    llm_client = LLMClient()
    research_orchestrator = ResearchOrchestrator()

    # Initialize forecast orchestrator
    forecast_orchestrator = ForecastOrchestrator(
        metaculus_client=metaculus_client,
        llm_client=llm_client,
        research_orchestrator=research_orchestrator,
    )

    # Get questions to forecast
    if args.question:
        # Single question mode
        logger.info(f"Forecasting single question ID: {args.question}")
        # Assume question_id == post_id for single question (most common case)
        open_question_id_post_id = [(args.question, args.question)]
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

    await forecast_orchestrator.forecast_questions(
        open_question_id_post_id=open_question_id_post_id,
        submit_prediction=submit_prediction,
        num_runs_per_question=num_runs_per_question,
        skip_previously_forecasted_questions=skip_previously_forecasted,
    )

    logger.info("Forecasting completed successfully")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
