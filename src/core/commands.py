from abc import ABC, abstractmethod

from src.core.settings import Settings


class BaseCommand(ABC):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @abstractmethod
    def execute(self) -> None:
        pass
