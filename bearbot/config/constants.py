"""Constants and static configuration."""

from __future__ import annotations


class TournamentIDs:
    """Tournament ID constants."""

    # AI Benchmarking Tournaments
    Q4_2024_AI_BENCHMARKING = 32506
    Q1_2025_AI_BENCHMARKING = 32627
    FALL_2025_AI_BENCHMARKING = "fall-aib-2025"
    SPRING_2026_AI_BENCHMARKING = "spring-aib-2026"
    CURRENT_MINIBENCH = "minibench"

    # Quarterly Cup Tournaments
    Q4_2024_QUARTERLY_CUP = 3672
    Q1_2025_QUARTERLY_CUP = 32630
    CURRENT_METACULUS_CUP = None  # TBD

    # Other Tournaments
    AXC_2025_TOURNAMENT = 32564
    AI_2027_TOURNAMENT = "ai-2027"


# Example questions for testing (question_id, post_id)
EXAMPLE_QUESTIONS: list[tuple[int, int]] = [
    (
        578,
        578,
    ),  # Human Extinction - Binary - https://www.metaculus.com/questions/578/human-extinction-by-2100/
    (
        14333,
        14333,
    ),  # Age of Oldest Human - Numeric - https://www.metaculus.com/questions/14333/age-of-oldest-human-as-of-2100/
    (
        22427,
        22427,
    ),  # Number of New Leading AI Labs - Multiple Choice - https://www.metaculus.com/questions/22427/number-of-new-leading-ai-labs/
    (
        38195,
        38880,
    ),  # Number of US Labor Strikes Due to AI in 2029 - Discrete - https://www.metaculus.com/c/diffusion-community/38880/how-many-us-labor-strikes-due-to-ai-in-2029/
]
