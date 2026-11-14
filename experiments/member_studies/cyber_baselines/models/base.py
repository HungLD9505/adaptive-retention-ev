"""Abstract base protocol for Cyber baseline forecasters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseForecaster(ABC):
    """Abstract interface for all benchmark models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier name."""

    @property
    @abstractmethod
    def param_count(self) -> int:
        """Total trainable parameter count."""

    @abstractmethod
    def predict(self, record: dict[str, Any]) -> list[float]:
        """Produce 24 hourly forecasts (normalized scaled energy) for the origin."""

    @abstractmethod
    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        """Online adaptation or refit when new day arrives."""
