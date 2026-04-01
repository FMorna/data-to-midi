from __future__ import annotations

from ..config import SourceConfig
from .base import BaseSource
from .random_walk import RandomWalkSource
from .stock import StockSource


class SourceRegistry:
    _sources: dict[str, type[BaseSource]] = {
        "random_walk": RandomWalkSource,
        "stock": StockSource,
    }

    @classmethod
    def create(cls, config: SourceConfig) -> BaseSource:
        source_type = config.type
        if source_type not in cls._sources:
            raise ValueError(
                f"Unknown source type: {source_type}. "
                f"Available: {list(cls._sources.keys())}"
            )

        if source_type == "random_walk":
            return RandomWalkSource(config.random_walk)
        elif source_type == "stock":
            return StockSource(config.stock)
        else:
            return cls._sources[source_type]()

    @classmethod
    def register(cls, name: str, source_cls: type[BaseSource]) -> None:
        cls._sources[name] = source_cls
