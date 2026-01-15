"""Multiple choice question forecaster."""

from __future__ import annotations

import asyncio
import datetime
import re

from langfuse import observe

from castor.clients.llm import LLMClient
from castor.exceptions import ParseError
from castor.research import Researcher

# Prompt template
MULTIPLE_CHOICE_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

The options are: {options}


Background:
{background}

{resolution_criteria}

{fine_print}


Your research assistant says:
{summary_report}

Today is {today}.

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The status quo outcome if nothing changed.
(c) A description of an scenario that results in an unexpected outcome.

You write your rationale remembering that (1) good forecasters put extra weight on \
the status quo outcome since the world changes slowly most of the time, and (2) good \
forecasters leave some moderate probability on most options to account for unexpected outcomes.

The last thing you write is your final probabilities for the N options in this order {options} as:
Option_A: Probability_A
Option_B: Probability_B
...
Option_N: Probability_N
"""


class MultipleChoiceForecaster:
    """Forecaster for multiple choice questions."""

    def __init__(
        self,
        llm_client: LLMClient,
        researcher: Researcher,
    ):
        """Initialize the multiple choice forecaster.

        Args:
            llm_client: Client for making LLM calls.
            researcher: Researcher for conducting research.
        """
        self.llm = llm_client
        self.research = researcher

    @observe(name="multiple-choice-forecaster", capture_input=False)
    async def forecast(
        self,
        question_details: dict,
        num_runs: int,
    ) -> tuple[dict[str, float], str]:
        """Generate a multiple choice forecast.

        Args:
            question_details: Question details from Metaculus API.
            num_runs: Number of forecast runs to perform (average is returned).

        Returns:
            Tuple of (dict mapping options to probabilities, comment string).
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details["resolution_criteria"]
        background = question_details["description"]
        fine_print = question_details["fine_print"]
        options = question_details["options"]

        summary_report = self.research.research(title)

        content = MULTIPLE_CHOICE_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
            options=options,
        )

        async def ask_llm_for_multiple_choice_probabilities_with_index(
            i: int, content: str
        ) -> tuple[dict[str, float], str]:
            rationale = await self.llm.call(
                content,
                trace_name="multiple-choice-llm-call",
                trace_metadata={"question_type": "multiple_choice", "run": i + 1},
            )

            option_probabilities = self._extract_option_probabilities(rationale, options)

            comment = (
                f"EXTRACTED_PROBABILITIES: {option_probabilities}\n\nGPT's Answer: "
                f"{rationale}\n\n\n"
            )

            probability_yes_per_category = self._generate_multiple_choice_forecast(
                options, option_probabilities
            )
            return probability_yes_per_category, comment

        probability_yes_per_category_and_comment_pairs = await asyncio.gather(
            *[
                ask_llm_for_multiple_choice_probabilities_with_index(i, content)
                for i in range(num_runs)
            ]
        )
        comments = [pair[1] for pair in probability_yes_per_category_and_comment_pairs]
        final_comment_sections = [
            f"## Rationale {i+1}\n{comment}" for i, comment in enumerate(comments)
        ]
        probability_yes_per_category_dicts: list[dict[str, float]] = [
            pair[0] for pair in probability_yes_per_category_and_comment_pairs
        ]
        average_probability_yes_per_category: dict[str, float] = {}
        for option in options:
            probabilities_for_current_option: list[float] = [
                dict[option] for dict in probability_yes_per_category_dicts
            ]
            average_probability_yes_per_category[option] = sum(
                probabilities_for_current_option
            ) / len(probabilities_for_current_option)

        final_comment = (
            f"Average Probability Yes Per Category: `{average_probability_yes_per_category}`\n\n"
            + "\n\n".join(final_comment_sections)
        )
        return average_probability_yes_per_category, final_comment

    @staticmethod
    def _extract_option_probabilities(forecast_text: str, options: list[str]) -> list[float]:
        """Extract option probabilities from LLM response.

        Args:
            forecast_text: The LLM's response text.
            options: List of option strings.

        Returns:
            List of probabilities (one per option).

        Raises:
            ParseError: If probabilities cannot be extracted.
        """

        def extract_option_probabilities(text):
            # Number extraction pattern
            number_pattern = r"-?\d+(?:,\d{3})*(?:\.\d+)?"

            results = []

            # Iterate through each line in the text
            for line in text.split("\n"):
                # Extract all numbers from the line
                numbers = re.findall(number_pattern, line)
                numbers_no_commas = [num.replace(",", "") for num in numbers]
                # Convert strings to float or int
                numbers = [
                    float(num) if "." in num else int(num) for num in numbers_no_commas
                ]
                # Add the tuple of numbers to results
                if len(numbers) >= 1:
                    last_number = numbers[-1]
                    results.append(last_number)

            return results

        option_probabilities = extract_option_probabilities(forecast_text)

        num_options = len(options)

        if len(option_probabilities) > 0:
            # return the last num_options items
            return list(option_probabilities[-num_options:])
        else:
            raise ParseError(
                f"Could not extract prediction from response: {forecast_text}"
            )

    @staticmethod
    def _generate_multiple_choice_forecast(
        options: list[str], option_probabilities: list[float]
    ) -> dict:
        """Generate a multiple choice forecast dictionary.

        Args:
            options: List of option strings.
            option_probabilities: List of probabilities.

        Returns:
            Dictionary mapping options to probabilities.

        Raises:
            ValueError: If number of options doesn't match probabilities.
        """
        # confirm that there is a probability for each option
        if len(options) != len(option_probabilities):
            raise ValueError(
                f"Number of options ({len(options)}) does not match "
                f"number of probabilities ({len(option_probabilities)})"
            )

        # Ensure we are using decimals
        total_sum = sum(option_probabilities)
        decimal_list = [x / total_sum for x in option_probabilities]

        def normalize_list(float_list):
            # Step 1: Clamp values
            clamped_list = [max(min(x, 0.99), 0.01) for x in float_list]

            # Step 2: Calculate the sum of all elements
            total_sum = sum(clamped_list)

            # Step 3: Normalize the list so that all elements add up to 1
            normalized_list = [x / total_sum for x in clamped_list]

            # Step 4: Adjust for any small floating-point errors
            adjustment = 1.0 - sum(normalized_list)
            normalized_list[-1] += adjustment

            return normalized_list

        normalized_option_probabilities = normalize_list(decimal_list)

        probability_yes_per_category = {}
        for i in range(len(options)):
            probability_yes_per_category[options[i]] = normalized_option_probabilities[i]

        return probability_yes_per_category
