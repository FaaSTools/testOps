from abc import ABC, abstractmethod
from typing import Dict, List


class InvokerInterface(ABC):
    @abstractmethod
    def run_experiment(self, *, deployment_dict: Dict, payload: List, repetitions_of_experiment: int = 1, repetitions_per_function: int = 1, concurrency: int = 1, **kwargs) -> Dict:
        '''this function runs the entire experiment
        inputs are directly taken from the input json.
        output is an extended deployment_dict'''
        pass

    @abstractmethod
    def invoke_single_function(self, *, function_name: str, payload: Dict, region: str, **kwargs):
        '''runs a single instance of a cloud function'''
        pass
