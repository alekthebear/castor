"""Question-related data models."""

from __future__ import annotations

from typing import Any


class QuestionDetails:
    """Wrapper for question details from Metaculus API.

    This is a simple wrapper around the dict returned by the API.
    In the future, this could be replaced with a proper Pydantic model.
    """

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default."""
        return self._data.get(key, default)

    @property
    def id(self) -> int:
        """Question ID."""
        return self._data["id"]

    @property
    def title(self) -> str:
        """Question title."""
        return self._data["title"]

    @property
    def type(self) -> str:
        """Question type (binary, numeric, discrete, multiple_choice)."""
        return self._data["type"]

    @property
    def description(self) -> str:
        """Question description/background."""
        return self._data.get("description", "")

    @property
    def resolution_criteria(self) -> str:
        """Resolution criteria."""
        return self._data.get("resolution_criteria", "")

    @property
    def fine_print(self) -> str:
        """Fine print."""
        return self._data.get("fine_print", "")

    def to_dict(self) -> dict[str, Any]:
        """Return underlying dictionary."""
        return self._data
