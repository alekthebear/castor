"""Forecasting logic for different question types."""

from castor.forecasting.binary import BinaryForecaster
from castor.forecasting.multiple_choice import MultipleChoiceForecaster
from castor.forecasting.numeric import NumericForecaster
from castor.forecasting.forecaster import Forecaster

__all__ = [
    "BinaryForecaster",
    "NumericForecaster",
    "MultipleChoiceForecaster",
    "Forecaster",
]
