"""Numeric and discrete question forecaster."""

from __future__ import annotations

import asyncio
import datetime
import re

import numpy as np
from langfuse import observe

from castor.clients.llm import LLMClient
from castor.exceptions import ParseError
from castor.models.distribution import NumericDistribution, Percentile
from castor.research import Researcher

# Prompt template
NUMERIC_PROMPT_TEMPLATE = """
You are a professional forecaster interviewing for a job.

Your interview question is:
{title}

Background:
{background}

{resolution_criteria}

{fine_print}

Units for answer: {units}

Your research assistant says:
{summary_report}

Today is {today}.

{lower_bound_message}
{upper_bound_message}


Formatting Instructions:
- CRITICAL: Your percentile values MUST be in the same numeric scale as the bounds above. \
If the bounds are in billions (e.g., 70,000,000,000), your answers must also be in billions, \
not thousands or millions.
- Please notice the units requested (e.g. whether you represent a number as 1,000,000 or 1m).
- Never use scientific notation.
- Always start with a smaller number (more negative if negative) and then increase from there

Before answering you write:
(a) The time left until the outcome to the question is known.
(b) The outcome if nothing changed.
(c) The outcome if the current trend continued.
(d) The expectations of experts and markets.
(e) A brief description of an unexpected scenario that results in a low outcome.
(f) A brief description of an unexpected scenario that results in a high outcome.

You remind yourself that good forecasters are humble and set wide 90/10 confidence \
intervals to account for unknown unknowns.

The last thing you write is your final answer as:
"
Percentile 10: XX
Percentile 20: XX
Percentile 40: XX
Percentile 60: XX
Percentile 80: XX
Percentile 90: XX
"
"""


class NumericForecaster:
    """Forecaster for numeric and discrete questions."""

    def __init__(
        self,
        llm_client: LLMClient,
        researcher: Researcher,
    ):
        """Initialize the numeric forecaster.

        Args:
            llm_client: Client for making LLM calls.
            researcher: Researcher for conducting research.
        """
        self.llm = llm_client
        self.research = researcher

    @observe(name="numeric-forecaster", capture_input=False)
    async def forecast(self, question_details: dict, num_runs: int) -> tuple[list[float], str]:
        """Generate a numeric/discrete forecast.

        Args:
            question_details: Question details from Metaculus API.
            num_runs: Number of forecast runs to perform (median is returned).

        Returns:
            Tuple of (CDF as list of floats, comment string).
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = question_details["title"]
        resolution_criteria = question_details["resolution_criteria"]
        background = question_details["description"]
        fine_print = question_details["fine_print"]
        question_type = question_details["type"]
        scaling = question_details["scaling"]
        open_upper_bound = question_details["open_upper_bound"]
        open_lower_bound = question_details["open_lower_bound"]
        unit_of_measure = (
            question_details["unit"]
            if question_details["unit"]
            else "Not stated (please infer this)"
        )
        upper_bound = scaling["range_max"]
        lower_bound = scaling["range_min"]
        zero_point = scaling["zero_point"]

        if question_type == "discrete":
            outcome_count = question_details["scaling"]["inbound_outcome_count"]
            cdf_size = outcome_count + 1
        else:
            cdf_size = 201

        # Create messages about the bounds - always show bounds for scale reference
        if open_lower_bound:
            lower_bound_message = (
                f"The question's lower bound is {lower_bound} (open - values below are possible)."
            )
        else:
            lower_bound_message = f"The outcome can not be lower than {lower_bound}."
        if open_upper_bound:
            upper_bound_message = (
                f"The question's upper bound is {upper_bound} (open - values above are possible)."
            )
        else:
            upper_bound_message = f"The outcome can not be higher than {upper_bound}."

        summary_report = self.research.research(title)

        content = NUMERIC_PROMPT_TEMPLATE.format(
            title=title,
            today=today,
            background=background,
            resolution_criteria=resolution_criteria,
            fine_print=fine_print,
            summary_report=summary_report,
            lower_bound_message=lower_bound_message,
            upper_bound_message=upper_bound_message,
            units=unit_of_measure,
        )

        async def ask_llm_to_get_cdf_with_index(i: int, content: str) -> tuple[list[float], str]:
            rationale = await self.llm.call(
                content,
                trace_name="numeric-llm-call",
                trace_metadata={"question_type": "numeric", "run": i + 1},
            )
            percentile_values = self._extract_percentiles(rationale)

            comment = (
                f"Extracted Percentile_values: {percentile_values}\n\nGPT's Answer: "
                f"{rationale}\n\n\n"
            )

            cdf = self._generate_continuous_cdf(
                percentile_values,
                question_type,
                open_upper_bound,
                open_lower_bound,
                upper_bound,
                lower_bound,
                zero_point,
                cdf_size,
            )

            return cdf, comment

        cdf_and_comment_pairs = await asyncio.gather(
            *[ask_llm_to_get_cdf_with_index(i, content) for i in range(num_runs)]
        )
        comments = [pair[1] for pair in cdf_and_comment_pairs]
        final_comment_sections = [
            f"## Rationale {i + 1}\n{comment}" for i, comment in enumerate(comments)
        ]
        cdfs: list[list[float]] = [pair[0] for pair in cdf_and_comment_pairs]
        all_cdfs = np.array(cdfs)
        median_cdf: list[float] = np.median(all_cdfs, axis=0).tolist()

        final_comment = f"Median CDF: `{str(median_cdf)[:100]}...`\n\n" + "\n\n".join(
            final_comment_sections
        )
        return median_cdf, final_comment

    @staticmethod
    def _extract_percentiles(forecast_text: str) -> dict:
        """Extract percentiles from LLM response.

        Args:
            forecast_text: The LLM's response text.

        Returns:
            Dictionary mapping percentile to value.

        Raises:
            ParseError: If percentiles cannot be extracted.
        """

        def extract_percentile_numbers(text) -> dict:
            pattern = r"^.*(?:P|p)ercentile.*$"
            number_pattern = (
                r"-\s*(?:[^\d\-]*\s*)?(\d+(?:,\d{3})*(?:\.\d+)?)|(\d+(?:,\d{3})*(?:\.\d+)?)"
            )
            results = []

            for line in text.split("\n"):
                if re.match(pattern, line):
                    numbers = re.findall(number_pattern, line)
                    numbers_no_commas = [
                        next(num for num in match if num).replace(",", "") for match in numbers
                    ]
                    numbers = [float(num) if "." in num else int(num) for num in numbers_no_commas]
                    if len(numbers) > 1:
                        first_number = numbers[0]
                        last_number = numbers[-1]
                        # Check if the original line had a negative sign before the last number
                        if "-" in line.split(":")[-1]:
                            last_number = -abs(last_number)
                        results.append((first_number, last_number))

            # Convert results to dictionary
            percentile_values = {}
            for first_num, second_num in results:
                key = first_num
                percentile_values[key] = second_num

            return percentile_values

        percentile_values = extract_percentile_numbers(forecast_text)

        if len(percentile_values) > 0:
            return percentile_values
        else:
            raise ParseError(f"Could not extract prediction from response: {forecast_text}")

    @staticmethod
    def _generate_continuous_cdf(
        percentile_values: dict,
        question_type: str,
        open_upper_bound: bool,
        open_lower_bound: bool,
        upper_bound: float,
        lower_bound: float,
        zero_point: float | None,
        cdf_size: int,
    ) -> list[float]:
        """Generate a continuous CDF from percentile values.

        Args:
            percentile_values: Dictionary mapping percentile to value.
            question_type: Type of question.
            open_upper_bound: Whether upper bound is open.
            open_lower_bound: Whether lower bound is open.
            upper_bound: Upper bound value.
            lower_bound: Lower bound value.
            zero_point: Zero point for log-scaled questions.
            cdf_size: Size of CDF to generate.

        Returns:
            List of 201 (or cdf_size) float values representing the CDF.
        """
        percentiles = []
        for percentile, value in percentile_values.items():
            percentiles.append(Percentile(percentile=percentile / 100, value=value))

        numeric_distribution = NumericDistribution(
            declared_percentiles=percentiles,
            open_upper_bound=open_upper_bound,
            open_lower_bound=open_lower_bound,
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            zero_point=zero_point,
            cdf_size=cdf_size,
        )
        cdf_as_objects = numeric_distribution.get_cdf()
        cdf_as_floats = [percentile.percentile for percentile in cdf_as_objects]

        return cdf_as_floats
