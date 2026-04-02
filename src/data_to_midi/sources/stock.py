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
        self._stale_counts: dict[str, int] = {s: 0 for s in self.symbols}

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
            raise ImportError("Install yfinance: pip install data-to-midi[stock]")

        while self._running:
            for symbol in self.symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    price = None
                    volume = 0

                    # Try intraday history first — gives actual minute-bar data
                    try:
                        hist = ticker.history(period="1d", interval="1m")
                        if not hist.empty:
                            price = float(hist["Close"].iloc[-1])
                            volume = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
                    except Exception:
                        pass

                    # Fall back to fast_info if history unavailable
                    if price is None:
                        info = ticker.fast_info
                        price = info.last_price
                        volume = getattr(info, "last_volume", 0) or 0

                    prev = self._last_prices.get(symbol, price)
                    change = price - prev
                    self._last_prices[symbol] = price

                    # Track stale data (price unchanged)
                    if abs(change) < 0.001:
                        self._stale_counts[symbol] = self._stale_counts.get(symbol, 0) + 1
                    else:
                        self._stale_counts[symbol] = 0

                    is_stale = self._stale_counts.get(symbol, 0) > 5

                    yield SourceSample(
                        timestamp=time.time(),
                        values={
                            "price": price,
                            "volume": volume,
                            "change": change,
                        },
                        metadata={
                            "source": "stock",
                            "symbol": symbol,
                            "stale": is_stale,
                        },
                    )
                except Exception as e:
                    print(f"  [stock] Failed to fetch {symbol}: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _stream_finnhub(self) -> AsyncIterator[SourceSample]:
        try:
            import finnhub
        except ImportError:
            raise ImportError("Install finnhub: pip install data-to-midi[stock]")

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
