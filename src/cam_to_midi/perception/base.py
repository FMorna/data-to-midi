from __future__ import annotations

from abc import ABC, abstractmethod

from ..sources.base import SourceSample
from .features import FeatureVector


class BasePerceptor(ABC):
    """Transforms raw SourceSamples into a FeatureVector."""

    @abstractmethod
    def update(self, sample: SourceSample) -> FeatureVector | None:
        """Feed a sample, return features when the window is full.

        Returns None if the window isn't full yet.
        """
        ...

    @abstractmethod
    def reset(self) -> None: ...
