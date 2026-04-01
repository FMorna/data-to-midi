from __future__ import annotations

from collections import deque

import numpy as np

from ..config import PerceptionConfig
from ..sources.base import SourceSample
from .base import BasePerceptor
from .extractors import (
    extract_change_rate,
    extract_density,
    extract_direction,
    extract_intensity,
    extract_periodicity,
    extract_volatility,
)
from .features import FeatureVector


class WindowedPerceptor(BasePerceptor):
    """Sliding-window feature extraction over a time series of prices."""

    def __init__(self, config: PerceptionConfig | None = None):
        config = config or PerceptionConfig()
        self.window_size = config.window_size
        self._prices: deque[float] = deque(maxlen=self.window_size)
        self._timestamps: deque[float] = deque(maxlen=self.window_size)

    def update(self, sample: SourceSample) -> FeatureVector | None:
        price = sample.values.get("price", 0.0)
        self._prices.append(price)
        self._timestamps.append(sample.timestamp)

        if len(self._prices) < self.window_size:
            return None

        prices = np.array(self._prices)

        return FeatureVector(
            timestamp=sample.timestamp,
            change_rate=extract_change_rate(prices),
            periodicity=extract_periodicity(prices),
            intensity=extract_intensity(prices),
            direction=extract_direction(prices),
            volatility=extract_volatility(prices),
            density=extract_density(prices),
        )

    def reset(self) -> None:
        self._prices.clear()
        self._timestamps.clear()
