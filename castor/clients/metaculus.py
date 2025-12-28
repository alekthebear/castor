"""Metaculus API client."""

from __future__ import annotations

import json
from typing import Optional

import requests

from castor.config.settings import settings
from castor.exceptions import MetaculusAPIError


class MetaculusClient:
    """Client for interacting with the Metaculus API."""

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the Metaculus client.

        Args:
            api_token: Metaculus API token. If not provided, uses settings.
            base_url: Base URL for Metaculus API. If not provided, uses settings.
        """
        self.api_token = api_token or settings.metaculus_token
        self.base_url = base_url or settings.api_base_url
        self.headers = {"Authorization": f"Token {self.api_token}"}

    def get_post_details(self, post_id: int) -> dict:
        """Get all details about a post from the Metaculus API.

        Args:
            post_id: The post ID to fetch.

        Returns:
            Dictionary containing post details.

        Raises:
            MetaculusAPIError: If the API request fails.
        """
        url = f"{self.base_url}/posts/{post_id}/"
        response = requests.get(url, headers=self.headers)

        if not response.ok:
            raise MetaculusAPIError(
                f"Failed to get post {post_id}: {response.status_code} {response.text}"
            )

        return json.loads(response.content)

    def list_posts_from_tournament(
        self,
        tournament_id: int | str,
        offset: int = 0,
        count: int = 50,
    ) -> dict:
        """List posts from a tournament.

        Args:
            tournament_id: The tournament ID (can be int or string slug).
            offset: Pagination offset.
            count: Number of posts to fetch.

        Returns:
            Dictionary containing posts data.

        Raises:
            MetaculusAPIError: If the API request fails.
        """
        url_qparams = {
            "limit": count,
            "offset": offset,
            "order_by": "-hotness",
            "forecast_type": ",".join(
                [
                    "binary",
                    "multiple_choice",
                    "numeric",
                    "discrete",
                ]
            ),
            "tournaments": [tournament_id],
            "statuses": "open",
            "include_description": "true",
        }
        url = f"{self.base_url}/posts/"
        response = requests.get(url, headers=self.headers, params=url_qparams)

        if not response.ok:
            raise MetaculusAPIError(
                f"Failed to list posts from tournament {tournament_id}: "
                f"{response.status_code} {response.text}"
            )

        return json.loads(response.content)

    def get_open_questions_from_tournament(
        self, tournament_id: int | str
    ) -> list[tuple[int, int]]:
        """Get list of open question IDs and post IDs from a tournament.

        Args:
            tournament_id: The tournament ID.

        Returns:
            List of (question_id, post_id) tuples.
        """
        posts = self.list_posts_from_tournament(tournament_id)

        post_dict = {}
        for post in posts["results"]:
            if question := post.get("question"):
                # single question post
                post_dict[post["id"]] = [question]

        open_question_id_post_id = []  # [(question_id, post_id)]
        for post_id, questions in post_dict.items():
            for question in questions:
                if question.get("status") == "open":
                    open_question_id_post_id.append((question["id"], post_id))

        return open_question_id_post_id

    def post_comment(
        self,
        post_id: int,
        comment_text: str,
        is_private: bool = True,
        included_forecast: bool = True,
    ) -> None:
        """Post a comment on a question.

        Args:
            post_id: The post ID to comment on.
            comment_text: The comment text.
            is_private: Whether the comment is private.
            included_forecast: Whether the comment includes a forecast.

        Raises:
            MetaculusAPIError: If the API request fails.
        """
        response = requests.post(
            f"{self.base_url}/comments/create/",
            json={
                "text": comment_text,
                "parent": None,
                "included_forecast": included_forecast,
                "is_private": is_private,
                "on_post": post_id,
            },
            headers=self.headers,
        )

        if not response.ok:
            raise MetaculusAPIError(
                f"Failed to post comment on post {post_id}: "
                f"{response.status_code} {response.text}"
            )

    def post_forecast(self, question_id: int, forecast_payload: dict) -> None:
        """Post a forecast on a question.

        Args:
            question_id: The question ID to forecast on.
            forecast_payload: The forecast payload (created by create_forecast_payload).

        Raises:
            MetaculusAPIError: If the API request fails.
        """
        url = f"{self.base_url}/questions/forecast/"
        response = requests.post(
            url,
            json=[
                {
                    "question": question_id,
                    **forecast_payload,
                },
            ],
            headers=self.headers,
        )

        if not response.ok:
            raise MetaculusAPIError(
                f"Failed to post forecast on question {question_id}: "
                f"{response.status_code} {response.text}"
            )

    @staticmethod
    def create_forecast_payload(
        forecast: float | dict[str, float] | list[float],
        question_type: str,
    ) -> dict:
        """Create a forecast payload for the Metaculus API.

        Args:
            forecast: The forecast value. Format depends on question type:
                - binary: float (probability)
                - multiple_choice: dict mapping option labels to probabilities
                - numeric/discrete: list of 201 CDF values
            question_type: The type of question (binary, multiple_choice, numeric, discrete).

        Returns:
            Dictionary in the format expected by the Metaculus API.
        """
        if question_type == "binary":
            return {
                "probability_yes": forecast,
                "probability_yes_per_category": None,
                "continuous_cdf": None,
            }
        if question_type == "multiple_choice":
            return {
                "probability_yes": None,
                "probability_yes_per_category": forecast,
                "continuous_cdf": None,
            }
        # numeric or discrete
        return {
            "probability_yes": None,
            "probability_yes_per_category": None,
            "continuous_cdf": forecast,
        }

    @staticmethod
    def forecast_is_already_made(post_details: dict) -> bool:
        """Check if a forecast has already been made on this question.

        Args:
            post_details: Post details from the API.

        Returns:
            True if a forecast has already been made, False otherwise.
        """
        try:
            forecast_values = post_details["question"]["my_forecasts"]["latest"][
                "forecast_values"
            ]
            return forecast_values is not None
        except (KeyError, TypeError):
            return False
