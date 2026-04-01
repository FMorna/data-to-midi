from __future__ import annotations

import asyncio
import os
import time
from typing import AsyncIterator

from ..config import StockConfig
from .base import BaseSource, SourceSample


class StockSource(BaseSource):
    """Live stock market data source.

    Uses yfinance for polling or finnhub for websocket streaming.
    """

    def __init__(self, config: StockConfig | None = None):
        config = config or StockConfig()
        self.symbols = config.symbols
        self.provider = config.provider
        self.poll_interval = config.poll_interval_sec
        self._running = False
        self._last_prices: dict[str, float] = {}

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def stream(self) -> AsyncIterator[SourceSample]:
        if self.provider == "yfinance":
            async for sample in self._stream_yfinance():
                yield sample
        elif self.provider == "finnhub":
            async for sample in self._stream_finnhub():
                yield sample
        else:
            raise ValueError(f"Unknown stock provider: {self.provider}")

    async def _stream_yfinance(self) -> AsyncIterator[SourceSample]:
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("Install yfinance: pip install cam-to-midi[stock]")

        while self._running:
            for symbol in self.symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.fast_info
                    price = info.last_price
                    prev = self._last_prices.get(symbol, price)
                    change = price - prev
                    self._last_prices[symbol] = price

                    yield SourceSample(
                        timestamp=time.time(),
                        values={
                            "price": price,
                            "volume": getattr(info, "last_volume", 0) or 0,
                            "change": change,
                        },
                        metadata={"source": "stock", "symbol": symbol},
                    )
                except Exception:
                    pass  # Skip failed ticks silently

            await asyncio.sleep(self.poll_interval)

    async def _stream_finnhub(self) -> AsyncIterator[SourceSample]:
        try:
            import finnhub
        except ImportError:
            raise ImportError("Install finnhub: pip install cam-to-midi[stock]")

        api_key = os.environ.get("FINNHUB_API_KEY", "")
        if not api_key:
            raise ValueError("Set FINNHUB_API_KEY environment variable")

        client = finnhub.Client(api_key=api_key)

        while self._running:
            for symbol in self.symbols:
                try:
                    quote = client.quote(symbol)
                    price = quote.get("c", 0)
                    prev = self._last_prices.get(symbol, price)
                    change = price - prev
                    self._last_prices[symbol] = price

                    yield SourceSample(
                        timestamp=time.time(),
                        values={
                            "price": price,
                            "volume": quote.get("v", 0),
                            "change": change,
                        },
                        metadata={"source": "stock", "symbol": symbol},
                    )
                except Exception:
                    pass

            await asyncio.sleep(self.poll_interval)
