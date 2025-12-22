"""Binary question forecaster."""

from __future__ import annotations

import asyncio
import datetime
import re

import numpy as np
from langfuse import observe

from bearbot.clients.llm import LLMClient
from bearbot.research import Researcher
from bearbot.exceptions import ParseError

# Prompt template
BINARY_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

Question background:
{background}


This question's outcome will be determined by the specific criteria below. These criteria have not yet been satisfied:
{resolution_criteria}

{fine_print}


Your research assistant says:
{summary_report}

Today is {today}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A brief description of a scenario that results in a No outcome.
(d) A brief description of a scenario that results in a Yes outcome.

You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time.

The last thing you write is your final answer as: "Probability: ZZ%", 0-100
"""


class BinaryForecaster:
    """Forecaster for binary questions."""

    def __init__(
        self,
        llm_client: LLMClient,
        researcher: Researcher,
    ):
        """Initialize the binary forecaster.

        Args:
            llm_client: Client for making LLM calls.
            research_orchestrator: Orchestrator for conducting research.
        """
        self.llm = llm_client
        self.research = researcher

    @observe(name="binary-forecaster", capture_input=False)
    async def forecast(
        self, question_details: dict, num_runs: int
    ) -> tuple[float, str]:
        """Generate a binary forecast.

        Args:
            question_details: Question details from Metaculus API.
            num_runs: Number of forecast runs to perform (median is returned).

        Returns:
            Tuple of (probability as decimal 0-1, comment string).
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details["resolution_criteria"]
        background = question_details["description"]
        fine_print = question_details["fine_print"]

        summary_report = self.research.research(title)

        content = BINARY_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
        )

        async def get_rationale_and_probability_with_index(
            i: int, content: str
        ) -> tuple[float, str]:
            rationale = await self.llm.call(
                content,
                trace_name="binary-llm-call",
                trace_metadata={"question_type": "binary", "run": i + 1},
            )

            probability = self._extract_probability(rationale)
            comment = (
                f"Extracted Probability: {probability}%\n\nGPT's Answer: "
                f"{rationale}\n\n\n"
            )
            return probability, comment

        probability_and_comment_pairs = await asyncio.gather(
            *[
                get_rationale_and_probability_with_index(i, content)
                for i in range(num_runs)
            ]
        )
        comments = [pair[1] for pair in probability_and_comment_pairs]
        final_comment_sections = [
            f"## Rationale {i+1}\n{comment}" for i, comment in enumerate(comments)
        ]
        probabilities = [pair[0] for pair in probability_and_comment_pairs]
        median_probability = float(np.median(probabilities)) / 100

        final_comment = f"Median Probability: {median_probability}\n\n" + "\n\n".join(
            final_comment_sections
        )
        return median_probability, final_comment

    @staticmethod
    def _extract_probability(forecast_text: str) -> float:
        """Extract probability from LLM response.

        Args:
            forecast_text: The LLM's response text.

        Returns:
            Probability as a percentage (0-100).

        Raises:
            ParseError: If probability cannot be extracted.
        """
        matches = re.findall(r"(\d+)%", forecast_text)
        if matches:
            # Return the last number found before a '%'
            number = int(matches[-1])
            number = min(99, max(1, number))  # clamp the number between 1 and 99
            return number
        else:
            raise ParseError(
                f"Could not extract prediction from response: {forecast_text}"
            )
