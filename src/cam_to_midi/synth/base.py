from __future__ import annotations

from abc import ABC, abstractmethod

import mido


class BaseSynth(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def send(self, message: mido.Message) -> None: ...

    @abstractmethod
    def set_instrument(self, channel: int, program: int) -> None: ...
