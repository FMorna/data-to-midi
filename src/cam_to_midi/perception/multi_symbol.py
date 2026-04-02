from __future__ import annotations

"""Multiplexed perceptor that maintains separate windows per stock symbol."""

from collections import deque
from typing import Dict, List, Tuple

from ..config import PerceptionConfig
from ..sources.base import SourceSample
from .base import BasePerceptor
from .features import FeatureVector
from .windowed import WindowedPerceptor


class MultiSymbolPerceptor(BasePerceptor):
    """Routes samples by symbol to separate WindowedPerceptors.

    Each symbol gets its own sliding window and feature extraction.
    Also maintains raw price history per symbol for the web UI chart.
    """

    def __init__(self, config: PerceptionConfig, symbols: list):
        self._config = config
        self._symbols = list(symbols)
        self._perceptors = {s: WindowedPerceptor(config) for s in self._symbols}
        # Price history: {symbol: deque of (timestamp, price)}
        self._price_history: dict = {s: deque(maxlen=500) for s in self._symbols}

    def update(self, sample: SourceSample):
        symbol = sample.metadata.get("symbol", "")
        price = sample.values.get("price", 0.0)

        # Track price history for chart
        if symbol in self._price_history:
            self._price_history[symbol].append((sample.timestamp, price))

        # Route to the correct perceptor
        if symbol not in self._perceptors:
            return None

        fv = self._perceptors[symbol].update(sample)
        if fv is not None:
            fv.symbol = symbol
        return fv

    def reset(self):
        for p in self._perceptors.values():
            p.reset()
        for h in self._price_history.values():
            h.clear()

    def get_latest_prices(self) -> dict:
        """Return {symbol: (timestamp, price)} for the most recent data point."""
        result = {}
        for symbol, history in self._price_history.items():
            if history:
                result[symbol] = history[-1]
        return result

    def get_price_history(self) -> dict:
        """Return full price history for chart initialization on reconnect."""
        return {s: list(h) for s, h in self._price_history.items()}

    @property
    def symbols(self) -> list:
        return self._symbols
