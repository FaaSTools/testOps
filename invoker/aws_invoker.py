import concurrent
import datetime
from typing import Dict, List
import json
import logging
from datetime import timezone
from time import perf_counter
from threading import current_thread
from concurrent.futures import ThreadPoolExecutor, wait

from invoker.invoker_interface import InvokerInterface
from Gen_Utils import print_neat_dict

import boto3


class AWSInvoker(InvokerInterface):

    def run_experiment(self, *, deployment_dict: Dict, payload: List, repetitions_of_experiment: int = 1, repetitions_per_function: int = 2, concurrency: int = 1, **kwargs) -> Dict:
        logging.debug('AWS::Run Experiment')
        print('AWS::Run Experiment')
        if 'AWS_regions' in deployment_dict:
            function_name = deployment_dict.get('function_name')
            for rep_experiment in range(repetitions_of_experiment):
                experiment_str = 'Experiment_' + str(rep_experiment)
                for region in deployment_dict['AWS_regions']:
                    if rep_experiment == 0:
                        for no_op_counter in range(50):
                            res = {'execution_start_utc': datetime.datetime.now(timezone.utc)}
                            start = perf_counter()
                            self.invoke_single_function(function_name='testOps_no_op_function', payload={}, region=region)
                            end = perf_counter()
                            res['execution_time'] = round((end - start) * 1000)
                            res['execution_end_utc'] = datetime.datetime.now(timezone.utc)
                            res['thread_name'] = f'testOps_no_op_function::{region}'
                            res['thread_ident'] = ''
                            dct = deployment_dict['AWS_regions'][region].get(experiment_str, {})
                            if not dct:
                                deployment_dict['AWS_regions'][region][experiment_str] = {'no_ops_function_' + str(no_op_counter): res}
                            else:
                                dct.update({'no_ops_function_' + str(no_op_counter): res})
                                deployment_dict['AWS_regions'][region][experiment_str] = dct
                    for mem_config in deployment_dict['AWS_regions'][region]['memory_configurations']:
                        result_list = []
                        full_function_name = function_name + '_' + str(mem_config) + 'MB'
                        print(full_function_name)
                        start = perf_counter()
                        with ThreadPoolExecutor(max_workers=concurrency) as executor:
                            counter = 0
                            result = []
                            for rep_function in range(repetitions_per_function):
                                result.append(executor.submit(self.__invoker_timed, full_function_name, payload[counter % len(payload)], region))
                                counter += 1

                            done, not_done = wait(result, return_when=concurrent.futures.ALL_COMPLETED)
                            for future in result:
                                print('this is your result:', future.result())
                                result_list.append(future.result())

                        end = perf_counter()
                        print('time running:', end - start)
                        dct = deployment_dict['AWS_regions'][region].get(experiment_str, {})
                        if not dct:
                            deployment_dict['AWS_regions'][region][experiment_str] = {mem_config: result_list}
                        else:
                            dct.update({mem_config: result_list})
                            deployment_dict['AWS_regions'][region][experiment_str] = dct
            print_neat_dict(deployment_dict)
        return deployment_dict

    def invoke_single_function(self, *, function_name: str, payload: Dict, region: str, **kwargs):
        """function to run a single lambda function"""
        aws_lambda = self.__lambda_client(region_name=region)

        log_type = kwargs.get('log_type', 'None')
        invocation_type = kwargs.get('invocation_type', 'RequestResponse')

        response = aws_lambda.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            LogType=log_type,
            Payload=json.dumps(payload),
        )

        # Decode response payload
        try:
            payload = response['Payload'].read(amt=None).decode('utf-8')
            response['Payload'] = json.loads(payload)
            logging.info(response)

        except (TypeError, json.decoder.JSONDecodeError):
            logging.error('Unable to parse Lambda Payload JSON response.')
            response['Payload'] = None

        return response

    def __lambda_client(self, region_name: str = 'us-east-1'):
        """Instantiate a thread-safe Lambda client"""
        session = boto3.session.Session()
        return session.client('lambda', region_name=region_name)

    def __invoker_timed(self, function_name: str, payload: Dict, region: str) -> Dict:
        res = {'execution_start_utc': datetime.datetime.now(timezone.utc)}
        thread = current_thread()

        start = perf_counter()
        response = self.invoke_single_function(function_name=function_name, payload=payload, invocation_type='RequestResponse', region=region)
        end = perf_counter()
        res['execution_time'] = round((end - start) * 1000)
        res['execution_end_utc'] = datetime.datetime.now(timezone.utc)
        res['thread_name'] = thread.name
        res['thread_ident'] = thread.ident
        res['status_code'] = response['StatusCode']
        res['response'] = response
        # execution_times[thread.name] = res
        return res
