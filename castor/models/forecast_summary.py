"""Short, human-readable summaries of Forecasts for list views."""

from __future__ import annotations

from typing import Any

MAX_OPTIONS_SHOWN = 3


def summarize_forecast(forecast: Any, question: dict[str, Any]) -> str:
    """Summarize a Forecast in one line according to its Question's type."""
    question_type = question["type"]
    if question_type == "binary":
        return f"{float(forecast):.0%}"
    if question_type == "multiple_choice":
        return _summarize_multiple_choice(forecast)
    if question_type in ("numeric", "discrete"):
        return _summarize_cdf(forecast, question)
    return str(forecast)[:80]


def _summarize_multiple_choice(forecast: dict[str, float]) -> str:
    ranked = sorted(forecast.items(), key=lambda item: item[1], reverse=True)
    shown = " · ".join(f"{option} {p:.0%}" for option, p in ranked[:MAX_OPTIONS_SHOWN])
    hidden = len(ranked) - MAX_OPTIONS_SHOWN
    return f"{shown} (+{hidden} more)" if hidden > 0 else shown


def _summarize_cdf(cdf: list[float], question: dict[str, Any]) -> str:
    """Median with an 80% interval, e.g. `42 [30–55] units`."""
    scaling = question["scaling"]
    p10, p50, p90 = (_quantile(cdf, q, scaling) for q in (0.1, 0.5, 0.9))
    unit = question.get("unit") or ""
    return f"{p50} [{p10}–{p90}] {unit}".strip()


def _quantile(cdf: list[float], q: float, scaling: dict[str, Any]) -> str:
    if q < cdf[0]:
        return f"<{_format_number(scaling['range_min'])}"
    if q > cdf[-1]:
        return f">{_format_number(scaling['range_max'])}"
    last = len(cdf) - 1
    for i in range(1, len(cdf)):
        if cdf[i] >= q:
            lo, hi = cdf[i - 1], cdf[i]
            fraction = (q - lo) / (hi - lo) if hi > lo else 0.0
            location = (i - 1 + fraction) / last
            return _format_number(_nominal_value(location, scaling))
    return _format_number(scaling["range_max"])


def _nominal_value(location: float, scaling: dict[str, Any]) -> float:
    """Map a position in [0, 1] on the question's axis to its real-world value."""
    range_min, range_max = scaling["range_min"], scaling["range_max"]
    zero_point = scaling.get("zero_point")
    if zero_point is None:
        return float(range_min + (range_max - range_min) * location)
    deriv_ratio = (range_max - zero_point) / (range_min - zero_point)
    growth = (deriv_ratio**location - 1) / (deriv_ratio - 1)
    return float(range_min + (range_max - range_min) * growth)


def _format_number(value: float) -> str:
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= threshold:
            return f"{value / threshold:.3g}{suffix}"
    return f"{value:.3g}"
