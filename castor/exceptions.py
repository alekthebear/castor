"""Custom exceptions for BearBot."""

from __future__ import annotations


class BearBotError(Exception):
    """Base exception for all BearBot errors."""

    pass


class MetaculusAPIError(BearBotError):
    """Error communicating with Metaculus API."""

    pass


class ResearchError(BearBotError):
    """Error during research phase."""

    pass


class LLMError(BearBotError):
    """Error calling LLM."""

    pass


class ParseError(BearBotError):
    """Error parsing LLM response."""

    pass


class ValidationError(BearBotError):
    """Error validating forecast."""

    pass
