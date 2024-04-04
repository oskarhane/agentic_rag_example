from abc import ABC, abstractmethod


class Retriever(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def invoke(self) -> str:
        pass


class AgenticRetriever(Retriever):
    def __init__(self):
        pass

    @abstractmethod
    def to_tools_dict(self) -> dict:
        pass
