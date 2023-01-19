from abc import ABC, abstractmethod
from typing import Dict


class AnalyzerInterface(ABC):

    @abstractmethod
    def analyze(self, *, deployment_dict: Dict, **kwargs) -> Dict:
        """Function to run the analyzer

        in: deployment_dict: Dict
        any number of kw arguments


        output is used for calculating Pareto Sets in form of a dict
        {'provider': 'AWS',
        'region': region,
        'MB': mem,
        'avg_RTT': int(current_mem_avg),
        'avg_no_op_rtt': int(no_op_avg),
        'avg_ET': int(ET_avg),
        'cost': cost,
        'measurement_points': len(all_rtt)
                                        }

        """
        pass