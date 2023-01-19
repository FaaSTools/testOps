import datetime
from datetime import timezone
from time import perf_counter
from typing import Dict, List
import uuid
import logging
import os

from AWS_Utils import invoke_lambda

from deployer.deployer_interface import DeployerInterface

from google.oauth2 import service_account
# from google.cloud import storage, functions_v1
import google.cloud.storage as storage
import google.cloud.functions_v1 as functions_v1
import google.cloud.exceptions as exceptions


class GCPDeployer(DeployerInterface):

    def deploy_no_op(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Function deployment')
        if 'GCP_regions' in deployment_dict:
            logging.debug('Function Deployment GCP')
            responses = []
            for region in deployment_dict['GCP_regions']:
                bucket_name = deployment_dict['GCP_regions'][region]['bucket_name']
                function_name = deployment_dict['function_name']
                handler_name = deployment_dict['gcp_handler']
                code_package_key = 'gs://' + bucket_name + '/' + deployment_dict['no_op_code'].split('/')[-1]
                function_memory_list = [128]
                logging.info('deploying to %s: %s' % (region, str(function_memory_list)))
                runtime = deployment_dict['gcp_runtime']
                print('memory gcp', function_memory_list)
                x = self.__gcp_deploy_from_google_cloud_storage(source_url=code_package_key,
                                                                region=region,
                                                                project_name=os.environ['GCP_PROJECT_ID'],
                                                                function_name=function_name,
                                                                function_handler=handler_name,
                                                                function_runtime=runtime,
                                                                memory_list=function_memory_list,
                                                                function_timeout=540,
                                                                is_no_op=True)
                print(x)
                responses.append(x)
            logging.info(responses)
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    def create_storage(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Storage creation')
        if 'GCP_regions' in deployment_dict:
            for region in deployment_dict['GCP_regions']:
                bucket_name = self.__create_google_cloud_bucket(region=region)
                deployment_dict['GCP_regions'][region]['bucket_name'] = bucket_name
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    def upload_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Function upload')
        if 'GCP_regions' in deployment_dict:
            if kwargs.get('is_no_op', False):
                pyStorage_payload = {'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
                                     'aws_secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
                                     'aws_session_token': os.environ['AWS_SESSION_TOKEN'],
                                     'source_url': deployment_dict['no_op_code'],
                                     'client_email': os.environ['GCP_CLIENT_EMAIL'],
                                     'private_key': os.environ['GCP_PRIVATE_KEY'],
                                     'project_id': os.environ['GCP_PROJECT_ID']}
            else:
                pyStorage_payload = {'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
                                     'aws_secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
                                     'aws_session_token': os.environ['AWS_SESSION_TOKEN'],
                                     'source_url': deployment_dict['gcp_code'],
                                     'client_email': os.environ['GCP_CLIENT_EMAIL'],
                                     'private_key': os.environ['GCP_PRIVATE_KEY'],
                                     'project_id': os.environ['GCP_PROJECT_ID']}
            pystorage_arn = deployment_dict['pyStorage_arn']

            # print('payload', print_neat_dict(pyStorage_payload))

            target_buckets = []
            reg = None
            bucket = None
            for region in deployment_dict['GCP_regions']:
                bucket_name = deployment_dict['GCP_regions'][region]['bucket_name']
                if kwargs.get('is_no_op', False):
                    gs_string = 'gs://' + bucket_name + '/' + deployment_dict['no_op_code'].split('/')[-1]
                else:
                    gs_string = 'gs://' + bucket_name + '/' + deployment_dict['gcp_code'].split('/')[-1]
                print('gs_string', gs_string)
                bucket = gs_string
                reg = region
                target_buckets.append(gs_string)

            pyStorage_payload['targets'] = target_buckets
            res = invoke_lambda(function_name=pystorage_arn, payload=pyStorage_payload,
                                invocation_type='RequestResponse', region='us-east-1')
            print('res:', res)
            if not kwargs.get('is_no_op', False):
                payload = res.get('Payload', None)
                if payload is not None:
                    data = payload.get('body')
                    print('data', data)
                    deployment_dict['GCP_regions'][reg]['code_upload_time'] = data.get(bucket)
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    def deploy_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Function deployment')
        print('GCP::Function deployment')
        if 'GCP_regions' in deployment_dict:
            logging.debug('Function Deployment GCP')
            responses = []
            for region in deployment_dict['GCP_regions']:
                print(region)
                bucket_name = deployment_dict['GCP_regions'][region]['bucket_name']
                function_name = deployment_dict['function_name']
                handler_name = deployment_dict['gcp_handler']
                code_package_key = 'gs://' + bucket_name + '/' + deployment_dict['gcp_code'].split('/')[-1]
                function_memory_list = deployment_dict['GCP_regions'][region]['memory_configurations']
                logging.info('deploying to %s: %s' % (region, str(function_memory_list)))
                runtime = deployment_dict['gcp_runtime']
                function_timeout = deployment_dict.get('gcp_function_timeout', 540)
                print('memory gcp', function_memory_list)
                response = self.__gcp_deploy_from_google_cloud_storage(source_url=code_package_key,
                                                                       region=region,
                                                                       project_name=os.environ['GCP_PROJECT_ID'],
                                                                       function_name=function_name,
                                                                       function_handler=handler_name,
                                                                       function_runtime=runtime,
                                                                       function_timeout=function_timeout,
                                                                       memory_list=function_memory_list)
                deployment_dict['GCP_regions'][region]['deployer_feedback'] = response
                responses.append(response)
            logging.info(responses)
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    # todo: this needs testing
    def delete_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Function deletion')
        if 'GCP_regions' in deployment_dict:
            project_name = deployment_dict['gcp_project_id']
            pareto = kwargs.get('pareto', None)
            if pareto is not None:
                for p in pareto:
                    if p.get('provider') == 'GCP':
                        self.__delete_google_cloud_function(region=p.get('region'),
                                                            function_name=deployment_dict['function_name'],
                                                            function_memory_list=list(p.get('MB')),
                                                            project_name=project_name)
            else:
                for region in deployment_dict['GCP_regions']:
                    self.__delete_google_cloud_function(region=region, function_name=deployment_dict['function_name'],
                                                        function_memory_list=deployment_dict['GCP_regions'][region][
                                                            'memory_configurations'], project_name=project_name)
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    def delete_storage(self, deployment_dict: Dict, **kwargs):
        logging.debug('GCP::Storage deletion')
        if 'GCP_regions' in deployment_dict:
            logging.debug('Bucket Deletion, GCP')
            for region in deployment_dict['GCP_regions']:
                self.__delete_google_cloud_bucket(bucket_name=deployment_dict['GCP_regions'][region]['bucket_name'])
        else:
            logging.info('Key \"GCP_regions\" not found in deployment_dict')

    def __google_cloud_functions_client(self):
        credentials = service_account.Credentials.from_service_account_file('google_credentials.json')
        return functions_v1.CloudFunctionsServiceClient(credentials=credentials)

    def __google_cloud_storage_client(self):
        credentials = service_account.Credentials.from_service_account_file('google_credentials.json')
        return storage.Client(credentials=credentials)

    def __create_google_cloud_bucket(self, *, bucket_name: str = None, region: str = None):
        bucket_client = self.__google_cloud_storage_client()
        if bucket_name is None:
            bucket_name = uuid.uuid4().hex

        retries = 3

        for counter in range(retries):
            try:
                if region is None:
                    bucket_client.create_bucket(bucket_or_name=bucket_name)
                else:
                    bucket_client.create_bucket(bucket_or_name=bucket_name, location=region)
                return bucket_name
            except exceptions.Conflict as e:
                print(bucket_name, e)
                logging.error(bucket_name)
                logging.error(e)
                bucket_name = uuid.uuid4().hex
                continue
        raise "Bucket creation retries limit reached"

    def __gcp_deploy_from_google_cloud_storage(self, *, source_url: str, region: str, project_name: str,
                                               function_name: str,
                                               function_handler: str, function_runtime: str, memory_list: List[int],
                                               function_timeout: int,
                                               is_no_op: bool = False):
        mem_response = []
        for memory_config in memory_list:
            time_measures = {'deployment_timestamp_utc_start': datetime.datetime.now(timezone.utc)}
            deployment_start = perf_counter()
            if memory_config not in [128, 256, 512, 1024, 2048, 4096, 8192]:
                continue
            self.__gcp_deploy_single_from_google_cloud_storage(source_url=source_url,
                                                                     region=region,
                                                                     project_name=project_name,
                                                                     function_name=function_name,
                                                                     function_handler=function_handler,
                                                                     function_runtime=function_runtime,
                                                                     memory_config=memory_config,
                                                                     is_no_op=is_no_op,
                                                                     function_timeout=function_timeout
                                                                     )
            time_measures['deployment_time'] = round((perf_counter() - deployment_start) * 1000)
            time_measures['deployment_timestamp_utc_end'] = datetime.datetime.now(timezone.utc)
            response = {'TimeMeasures': time_measures}
            mem_response.append({memory_config: response})
        return mem_response

    def __gcp_deploy_single_from_google_cloud_storage(self, *, source_url: str, region: str, project_name: str,
                                                      function_name: str, function_handler: str, function_runtime: str,
                                                      memory_config: int, function_timeout: int,
                                                      is_no_op: bool = False):
        client = self.__google_cloud_functions_client()

        function_name = function_name + '_' + str(memory_config) + 'MB'
        if is_no_op:
            full_function_name = f'projects/{project_name}/locations/{region}/functions/testOps_no_op_function'
        else:
            full_function_name = f'projects/{project_name}/locations/{region}/functions/{function_name}'
        location_string = f'projects/{project_name}/locations/{region}'
        f = functions_v1.CloudFunction()
        f.source_archive_url = source_url
        f.name = full_function_name

        f.timeout = datetime.timedelta(seconds=function_timeout)
        f.entry_point = function_handler
        f.runtime = function_runtime
        f.available_memory_mb = memory_config
        trigger = functions_v1.HttpsTrigger()
        trigger.url = 'https://' + full_function_name
        trigger.security_level = 'SECURE_ALWAYS'
        f.https_trigger = trigger

        request = functions_v1.CreateFunctionRequest(
            location=location_string,
            function=f

        )
        try:
            op = client.create_function(request=request)
            print('Deploying function...')
            logging.info('Deploying function... %s in %s with %d MB Ram' % (function_name, region, memory_config))
            response = op.result()
            logging.info(response)
        except Exception as e:
            logging.error(e)
            return None
        return response

    def __delete_google_cloud_bucket(self, *, bucket_name: str):
        bucket_client = self.__google_cloud_storage_client()
        bucket = bucket_client.get_bucket(bucket_name)
        try:
            bucket.delete(force=True)
        except exceptions.NotFound as e:
            logging.error(e)

    # todo: this needs testing
    def __delete_google_cloud_function(self, *, region: str, function_name: str, function_memory_list: List,
                                       project_name: str):
        client = self.__google_cloud_functions_client()
        for memory_config in function_memory_list:
            function_name = function_name + '_' + str(memory_config) + 'MB'
            full_function_name = f'projects/{project_name}/locations/{region}/functions/{function_name}'
            # request = functions_v1.DeleteFunctionRequest()
            try:
                op = client.delete_function(name=full_function_name)
                print('Deleting function...')
                logging.info('Deleting function... %s in %s with %d MB Ram' % (function_name, region, memory_config))
                response = op.result()
                logging.info(response)
            except Exception as e:
                logging.error(e)
                return None
