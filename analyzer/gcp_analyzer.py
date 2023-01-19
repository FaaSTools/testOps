import logging
from _decimal import Decimal
from typing import Dict, List
from decimal import *

from analyzer.analyzer_interface import AnalyzerInterface


class GCPAnalyzer(AnalyzerInterface):
    def analyze(self, *, deployment_dict: Dict, assumed_invocations: int = 1000000, **kwargs):
        getcontext().prec = 10
        logging.debug('GCP::Calculate Cost')
        print('GCP::Calculate Cost')
        #  Values taken from https://cloud.google.com/functions/pricing
        invocation_cost = Decimal(0.0000004)
        duration_gb_ps_cost_t1 = Decimal(0.0000025)
        duration_ghz_ps_cost_t1 = Decimal(0.0000100)
        duration_gb_ps_cost_t2 = Decimal(0.0000035)
        duration_ghz_ps_cost_t2 = Decimal(0.0000140)
        cpu_dict = {128: 200, 256: 400, 512: 800, 1024: 1400, 2048: 2800, 4096: 4800, 8192: 4800}
        t1_regions = ['asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'europe-north1', 'europe-west1',
                      'europe-west2', 'europe-west4', 'us-central1', 'us-east1', 'us-east4', 'us-west1']

        results_all = []
        if 'GCP_regions' in deployment_dict:
            for region in deployment_dict['GCP_regions']:
                if region in t1_regions:
                    print('t1')
                    duration_gb_ps_cost = duration_gb_ps_cost_t1
                    duration_ghz_ps_cost = duration_ghz_ps_cost_t1
                else:
                    print('t2')
                    duration_gb_ps_cost = duration_gb_ps_cost_t2
                    duration_ghz_ps_cost = duration_ghz_ps_cost_t2
                mem_configs = deployment_dict['GCP_regions'][region].get('memory_configurations')
                exp0 = deployment_dict['GCP_regions'][region].get('Experiment_0')
                no_op_list = []
                for key in exp0.keys():
                    if str(key).startswith('no_ops_function_'):
                        no_op_list.append(exp0.get(key))
                no_op_list.pop(0)
                no_op_avg = self.__calculcate_average_time(no_op_list, True)
                experiment_list = []
                for experiment in deployment_dict['GCP_regions'][region]:
                    if experiment.startswith('Experiment_'):
                        experiment_list.append(experiment)

                for mem in mem_configs:
                    all_rtt = []
                    for current_experiment in experiment_list:
                        current_invokations = deployment_dict['GCP_regions'][region].get(current_experiment).get(
                            str(mem))
                        if current_invokations is None:
                            current_invokations = deployment_dict['GCP_regions'][region].get(current_experiment).get(mem)
                        all_rtt.extend(current_invokations)

                    current_mem_avg = self.__calculcate_average_time(all_rtt)
                    ET_avg = current_mem_avg - no_op_avg
                    cost = self.__calculate_function_cost(assumed_invocations, ET_avg, mem, invocation_cost,
                                                          duration_gb_ps_cost, duration_ghz_ps_cost, cpu_dict)
                    results_all.append({
                        'provider': 'GCP',
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

    def __calculate_function_cost(self, requests: int, avg_et: Decimal, memory: int, invocation_cost: Decimal, duration_gb_ps_cost: Decimal, duration_ghz_ps_cost: Decimal, cpu_dict: Dict):
        getcontext().prec = 10
        gbs_seconds = Decimal(Decimal(memory / 1024) * (avg_et * Decimal(0.001)))
        ghz_seconds = Decimal(Decimal(cpu_dict.get(memory) / 1000) * (avg_et * Decimal(0.001)))
        gbs_seconds_monthly = gbs_seconds * requests
        ghz_seconds_monthly = ghz_seconds * requests
        monthly_request_charges = requests * invocation_cost
        monthly_memory_charges = gbs_seconds_monthly * duration_gb_ps_cost
        monthly_cpu_charges = ghz_seconds_monthly * duration_ghz_ps_cost
        return round(float(monthly_request_charges + monthly_memory_charges + monthly_cpu_charges), 2)
