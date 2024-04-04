from abc import abstractmethod
from retrievers.retriever import Retriever


class AgenticRetriever(Retriever):
    def __init__(self):
        pass

    @abstractmethod
    def to_tools_dict(self) -> dict:
        pass
