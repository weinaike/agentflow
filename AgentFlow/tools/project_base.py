from abc import ABC, abstractmethod

class ProjectBase:
    
    @abstractmethod
    def __hash__(self) -> str:
        pass

    def __eq__(self, other) -> bool:
        if isinstance(other, ProjectBase):
            return self.__hash__() == other.__hash__()
        return False    

    @abstractmethod
    def parse(self):
        pass

    @abstractmethod
    def find_definition(self, symbol: str, type: str=None):
        pass    

    @abstractmethod
    def fetch_source_code(self, symbol: str, type: str=None):
        pass

    @abstractmethod
    def get_call_graph(self, symbol: str, type: str=None):
        pass