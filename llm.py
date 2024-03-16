from abc import ABC, abstractmethod


class LLM(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def invoke(self):
        pass

    @abstractmethod
    def get_embedding(self):
        pass
