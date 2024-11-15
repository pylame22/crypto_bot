from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    async def disconnect(self) -> None:
        pass
