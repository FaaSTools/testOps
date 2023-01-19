import logging
from _decimal import Decimal
from typing import Dict, List
from decimal import *

from analyzer.analyzer_interface import AnalyzerInterface


class AWSAnalyzer(AnalyzerInterface):
    def analyze(self, *, deployment_dict: Dict, assumed_invocations: int = 1000000, **kwargs):
        getcontext().prec = 10
        logging.debug('AWS::Analyze')
        print('AWS::Analyze')
        invocation_cost = Decimal(0.0000002)
        duration_gb_ps_cost = Decimal(0.0000166667)
        results_all = []
        if 'AWS_regions' in deployment_dict:
            for region in deployment_dict['AWS_regions']:
                mem_configs = deployment_dict['AWS_regions'][region].get('memory_configurations')
                exp0 = deployment_dict['AWS_regions'][region].get('Experiment_0')
                no_op_list = []
                for key in exp0.keys():
                    if str(key).startswith('no_ops_function_'):
                        no_op_list.append(exp0.get(key))
                no_op_list.pop(0)
                no_op_avg = self.__calculcate_average_time(no_op_list, True)
                experiment_list = []
                for experiment in deployment_dict['AWS_regions'][region]:
                    if experiment.startswith('Experiment_'):
                        experiment_list.append(experiment)

                print('ex list', experiment_list)
                for mem in mem_configs:
                    all_rtt = []
                    for current_experiment in experiment_list:
                        current_invokations = deployment_dict['AWS_regions'][region].get(current_experiment).get(str(mem))
                        if current_invokations is None:
                            current_invokations = deployment_dict['AWS_regions'][region].get(current_experiment).get(mem)
                        print(deployment_dict['AWS_regions'][region].get(current_experiment))
                        print(mem, current_experiment, all_rtt, current_invokations)
                        all_rtt.extend(current_invokations)

                    current_mem_avg = self.__calculcate_average_time(all_rtt)
                    ET_avg = current_mem_avg - no_op_avg
                    name = 'AWS_' + region + '_MB' + str(mem)
                    cost = self.__calculate_function_cost(assumed_invocations, ET_avg, mem, invocation_cost,
                                                          duration_gb_ps_cost)
                    results_all.append({
                        'provider': 'AWS',
                        'region': region,
                        'MB': mem,
                        'avg_RTT': int(current_mem_avg),
                        'avg_no_op_rtt': int(no_op_avg),
                        'avg_ET': int(ET_avg),
                        'cost': cost,
                        'measurement_points': len(all_rtt)
                                        })
        return results_all

    def __calculcate_average_time(self, measurement_list: List, is_no_op: bool = False) -> Decimal:
        getcontext().prec = 10
        counter = 0
        time_sum = Decimal(0)
        if is_no_op:
            for x in measurement_list:
                time_sum = time_sum + Decimal(x.get('execution_time'))
                counter += 1
        else:
            thread_list = []
            for x in measurement_list:
                t_id = x.get('thread_ident')
                if t_id in thread_list:
                    time_sum = time_sum + Decimal(x.get('execution_time'))
                    counter += 1
                else:
                    thread_list.append(t_id)
        return time_sum / counter

    def __calculate_function_cost(self, requests: int, avg_et: Decimal, memory: int, invocation_cost: Decimal, duration_gb_ps_cost: Decimal):
        getcontext().prec = 10
        allocated_mem_in_gb = memory * Decimal(0.0009765625)
        total_compute_seconds = requests * (avg_et * Decimal(0.001))
        total_compute_gb_seconds = allocated_mem_in_gb * total_compute_seconds
        monthly_compute_charges = total_compute_gb_seconds * duration_gb_ps_cost
        monthly_request_charges = requests * invocation_cost

        return round(float(monthly_request_charges + monthly_compute_charges), 2)
