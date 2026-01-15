"""Script to fetch tournament questions with timing information.

Usage:
    uv run python scripts/get_tournament_questions.py <tournament_id>
    uv run python scripts/get_tournament_questions.py <tournament_id> --json-only
    uv run python scripts/get_tournament_questions.py <tournament_id> -o output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from castor.config.settings import settings


@dataclass
class QuestionData:
    """Data extracted from a tournament question.

    Add new fields here as needed for future analysis.
    """

    id: int
    title: str
    type: str
    status: str
    # Timing fields
    open_time: str | None = None
    cp_reveal_time: str | None = None
    scheduled_close_time: str | None = None
    actual_close_time: str | None = None
    resolution_known_time: str | None = None
    # Computed fields
    open_to_close: str = "N/A"
    # Raw data for future expansion
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding private fields."""
        result = asdict(self)
        del result["_raw"]
        return result

    @classmethod
    def from_api_response(cls, question: dict[str, Any]) -> QuestionData:
        """Create QuestionData from API response."""
        open_time = question.get("open_time")
        scheduled_close_time = question.get("scheduled_close_time")
        actual_close_time = question.get("actual_close_time")

        close_time_for_calc = actual_close_time or scheduled_close_time
        open_to_close = calculate_duration(open_time, close_time_for_calc)

        return cls(
            id=question.get("id", 0),
            title=question.get("title", "N/A"),
            type=question.get("type", "N/A"),
            status=question.get("status", "N/A"),
            open_time=open_time,
            cp_reveal_time=question.get("cp_reveal_time"),
            scheduled_close_time=scheduled_close_time,
            actual_close_time=actual_close_time,
            resolution_known_time=(
                question.get("resolution_known_at") or question.get("resolution_known_time")
            ),
            open_to_close=open_to_close,
            _raw=question,
        )


def fetch_tournament_posts(tournament_id: str) -> list[dict[str, Any]]:
    """Fetch all posts from a tournament (not just open ones)."""
    headers = {"Authorization": f"Token {settings.metaculus_token}"}
    base_url = settings.api_base_url

    all_posts: list[dict[str, Any]] = []
    offset = 0
    page_size = 100

    while True:
        params: dict[str, Any] = {
            "limit": page_size,
            "offset": offset,
            "order_by": "-hotness",
            "forecast_type": ",".join(["binary", "multiple_choice", "numeric", "discrete"]),
            "tournaments": [tournament_id],
            "include_description": "true",
        }
        url = f"{base_url}/posts/"
        response = requests.get(url, headers=headers, params=params)

        if not response.ok:
            print(f"Error: {response.status_code} {response.text}", file=sys.stderr)
            sys.exit(1)

        data = response.json()
        posts = data.get("results", [])
        all_posts.extend(posts)

        if len(posts) < page_size:
            break
        offset += page_size

    return all_posts


def format_datetime(dt_str: str | None) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return dt_str


def calculate_duration(start_str: str | None, end_str: str | None) -> str:
    """Calculate duration between two datetime strings."""
    if not start_str or not end_str:
        return "N/A"
    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        delta = end - start
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes = remainder // 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except ValueError:
        return "N/A"


def extract_questions(posts: list[dict[str, Any]]) -> list[QuestionData]:
    """Extract question data from posts."""
    questions = []
    for post in posts:
        question = post.get("question")
        if question:
            questions.append(QuestionData.from_api_response(question))
    return questions


def print_questions(questions: list[QuestionData]) -> None:
    """Print questions to console."""
    print("=" * 100)
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q.title}")
        print(f"   ID: {q.id}")
        print(f"   Type: {q.type}")
        print(f"   Status: {q.status}")
        print(f"   Open Time:            {format_datetime(q.open_time)}")
        print(f"   CP Reveal Time:       {format_datetime(q.cp_reveal_time)}")
        print(f"   Scheduled Close Time: {format_datetime(q.scheduled_close_time)}")
        print(f"   Actual Close Time:    {format_datetime(q.actual_close_time)}")
        print(f"   Resolution Known:     {format_datetime(q.resolution_known_time)}")
        print(f"   Open to Close:        {q.open_to_close}")
        print("-" * 80)


def print_summary(questions: list[QuestionData]) -> None:
    """Print summary statistics."""
    print("\nSummary:")
    print(f"  Total questions: {len(questions)}")

    types = Counter(q.type for q in questions)
    statuses = Counter(q.status for q in questions)

    print(f"  By type: {dict(types)}")
    print(f"  By status: {dict(statuses)}")


def save_to_json(questions: list[QuestionData], output_path: Path) -> None:
    """Save questions to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump([q.to_dict() for q in questions], f, indent=2)
    print(f"\nData saved to: {output_path}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch tournament questions with timing information.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/get_tournament_questions.py aibq4
  uv run python scripts/get_tournament_questions.py aibq4 --json-only
  uv run python scripts/get_tournament_questions.py aibq4 -o data/questions.json
        """,
    )
    parser.add_argument(
        "tournament_id",
        help="Tournament ID or slug (e.g., 'aibq4', 'spring-aib-2026')",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file path (default: tournament_<id>_questions.json)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only output JSON, skip console printing",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    tournament_id = args.tournament_id
    output_path = args.output or Path(f"tournament_{tournament_id}_questions.json")

    if not args.json_only:
        print(f"Fetching questions from tournament: {tournament_id}\n")

    posts = fetch_tournament_posts(tournament_id)

    if not posts:
        print("No posts found in tournament.", file=sys.stderr)
        sys.exit(1)

    questions = extract_questions(posts)

    if not args.json_only:
        print(f"Found {len(questions)} questions\n")
        print_questions(questions)
        print_summary(questions)

    save_to_json(questions, output_path)


if __name__ == "__main__":
    main()
