"""Forecasting logic for different question types."""

from bearbot.forecasting.binary import BinaryForecaster
from bearbot.forecasting.multiple_choice import MultipleChoiceForecaster
from bearbot.forecasting.numeric import NumericForecaster
from bearbot.forecasting.forecaster import Forecaster

__all__ = [
    "BinaryForecaster",
    "NumericForecaster",
    "MultipleChoiceForecaster",
    "Forecaster",
]
