from abc import ABC, abstractmethod


class AbstractSceneController(ABC):

    @abstractmethod
    def create_scene(self, *args, **kwargs):
        pass

    @abstractmethod
    def run_simulation(self, *args, **kwargs):
        pass
