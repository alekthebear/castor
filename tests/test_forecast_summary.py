import numpy as np

from castor.models.forecast_summary import summarize_forecast


def test_binary():
    assert summarize_forecast(0.734, {"type": "binary"}) == "73%"


def test_multiple_choice_shows_top_options():
    forecast = {"A": 0.1, "B": 0.4, "C": 0.3, "D": 0.15, "E": 0.05}
    summary = summarize_forecast(forecast, {"type": "multiple_choice"})
    assert summary == "B 40% · C 30% · D 15% (+2 more)"


def test_multiple_choice_with_few_options():
    summary = summarize_forecast({"Yes": 0.7, "No": 0.3}, {"type": "multiple_choice"})
    assert summary == "Yes 70% · No 30%"


def _question(zero_point=None, unit="units"):
    return {
        "type": "numeric",
        "unit": unit,
        "scaling": {"range_min": 0, "range_max": 100, "zero_point": zero_point},
    }


def test_numeric_uniform_linear():
    cdf = np.linspace(0, 1, 201).tolist()
    assert summarize_forecast(cdf, _question()) == "50 [10–90] units"


def test_numeric_mass_outside_bounds():
    cdf = np.linspace(0.2, 0.85, 201).tolist()
    summary = summarize_forecast(cdf, _question(unit=""))
    assert summary.startswith("46.2 [<0–>100]")


def test_numeric_log_scaled():
    question = {
        "type": "numeric",
        "unit": "",
        "scaling": {"range_min": 1, "range_max": 1_000_000, "zero_point": 0},
    }
    cdf = np.linspace(0, 1, 201).tolist()
    # Uniform in log space: the median is the geometric midpoint
    assert summarize_forecast(cdf, question).startswith("1k [")


def test_discrete_uses_its_own_cdf_size():
    question = {
        "type": "discrete",
        "unit": "",
        "scaling": {"range_min": 0, "range_max": 10, "zero_point": None},
    }
    cdf = np.linspace(0, 1, 12).tolist()
    assert summarize_forecast(cdf, question) == "5 [1–9]"
