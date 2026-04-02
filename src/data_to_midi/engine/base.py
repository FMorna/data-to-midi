from __future__ import annotations

from abc import ABC, abstractmethod

import mido

from ..mapping.musical_params import MusicalEvent


class BaseMusicEngine(ABC):
    @abstractmethod
    def process(self, event: MusicalEvent) -> list[mido.Message]: ...

    @abstractmethod
    def set_key(self, root: str, scale: str) -> None: ...

    @abstractmethod
    def set_tempo(self, bpm: float) -> None: ...
