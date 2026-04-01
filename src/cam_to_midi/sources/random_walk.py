from __future__ import annotations

import asyncio
import random
import time
from typing import AsyncIterator

from ..config import RandomWalkConfig
from .base import BaseSource, SourceSample


class RandomWalkSource(BaseSource):
    """Synthetic Brownian-motion price data for testing without APIs."""

    def __init__(self, config: RandomWalkConfig | None = None):
        config = config or RandomWalkConfig()
        self.tick_interval = config.tick_interval_sec
        self.volatility = config.volatility
        self.price = config.initial_price
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def stream(self) -> AsyncIterator[SourceSample]:
        while self._running:
            # Geometric Brownian motion step
            change = self.price * self.volatility * random.gauss(0, 1)
            self.price = max(0.01, self.price + change)

            # Synthetic volume correlated with price movement magnitude
            volume = abs(change) * random.uniform(800, 1200) / self.volatility

            yield SourceSample(
                timestamp=time.time(),
                values={
                    "price": self.price,
                    "volume": volume,
                    "change": change,
                },
                metadata={"source": "random_walk"},
            )
            await asyncio.sleep(self.tick_interval)
