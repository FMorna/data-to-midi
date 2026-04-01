from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class SourceSample:
    """Universal data packet emitted by any source."""

    timestamp: float
    values: dict[str, float]
    metadata: dict[str, str] = field(default_factory=dict)


class BaseSource(ABC):
    """Async generator that yields SourceSamples."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def stream(self) -> AsyncIterator[SourceSample]: ...
