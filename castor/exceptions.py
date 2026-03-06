"""Custom exceptions for Castor."""

from __future__ import annotations


class CastorError(Exception):
    """Base exception for all Castor errors."""

    pass


class MetaculusAPIError(CastorError):
    """Error communicating with Metaculus API."""

    pass


class ResearchError(CastorError):
    """Error during research phase."""

    pass


class LLMError(CastorError):
    """Error calling LLM."""

    pass


class ParseError(CastorError):
    """Error parsing LLM response."""

    pass


class ValidationError(CastorError):
    """Error validating forecast."""

    pass
