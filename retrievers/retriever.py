from abc import ABC, abstractmethod


class Retriever(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def invoke(self) -> str:
        pass
