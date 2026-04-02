from __future__ import annotations

from abc import ABC, abstractmethod

from ..perception.features import FeatureVector
from .musical_params import MusicalEvent


class BaseMapper(ABC):
    """Maps a FeatureVector to a MusicalEvent."""

    @abstractmethod
    def map(self, features: FeatureVector) -> MusicalEvent: ...
