"""Storage for Questions and recorded Forecast Runs."""

from castor.storage.repository import RunRecord, get_engine, save_run

__all__ = ["RunRecord", "get_engine", "save_run"]
