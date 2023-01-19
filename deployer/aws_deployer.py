import logging

from AWS_Utils import invoke_lambda
from deployer.deployer_interface import DeployerInterface

from typing import Dict, List
import boto3
import botocore.exceptions
import uuid
import os
from time import perf_counter
import datetime
from datetime import timezone


class AWSDeployer(DeployerInterface):

    def deploy_no_op(self, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::No_OP Function deployment')
        if 'AWS_regions' in deployment_dict:
            responses = []
            for region in deployment_dict['AWS_regions']:
                bucket_name = deployment_dict['AWS_regions'][region]['bucket_name']
                role_arn = deployment_dict['aws_deployment_role']
                function_name = 'testOps_no_op_function'
                handler_name = deployment_dict['no_op_handler_aws']
                code_package_key = deployment_dict['no_op_code'].split('/')[-1]
                function_memory_list = [128]
                logging.info('deploying no_op to %s: %s' % (region, str(function_memory_list)))
                runtime = deployment_dict['aws_runtime']
                x = self.__aws_deploy_from_s3_v2(function_name=function_name, role_arn=role_arn,
                                                 handler_name=handler_name,
                                                 code_package_key=code_package_key, function_timeout=300,
                                                 runtime=runtime,
                                                 function_memory_list=function_memory_list, s3_bucket_name=bucket_name,
                                                 s3_region=region, is_no_op=True)
                responses.append(x)
            logging.info(responses)
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')

    def create_storage(self, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::Storage creation')
        if 'AWS_regions' in deployment_dict:
            for region in deployment_dict['AWS_regions']:
                bucket_name = self.__create_aws_bucket(region=region)
                deployment_dict['AWS_regions'][region]['bucket_name'] = bucket_name
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')

    def upload_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::Function upload')
        if 'AWS_regions' in deployment_dict:
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
                                     'source_url': deployment_dict['aws_code'],
                                     'client_email': os.environ['GCP_CLIENT_EMAIL'],
                                     'private_key': os.environ['GCP_PRIVATE_KEY'],
                                     'project_id': os.environ['GCP_PROJECT_ID']}
            pystorage_arn = deployment_dict['pyStorage_arn']

            target_buckets = []
            reg = None
            bucket = None
            for region in deployment_dict['AWS_regions']:
                bucket_name = deployment_dict['AWS_regions'][region]['bucket_name']
                if kwargs.get('is_no_op', False):
                    s3_string = 's3://' + bucket_name + '/' + deployment_dict['no_op_code'].split('/')[-1]
                else:
                    s3_string = 's3://' + bucket_name + '/' + deployment_dict['aws_code'].split('/')[-1]
                print('s3_string', s3_string)
                bucket = s3_string
                reg = region
                target_buckets.append(s3_string)

            pyStorage_payload['targets'] = target_buckets

            res = invoke_lambda(function_name=pystorage_arn, payload=pyStorage_payload,
                                invocation_type='RequestResponse', region='us-east-1')
            print('res:', res)
            if not kwargs.get('is_no_op', False):
                payload = res.get('Payload', None)
                if payload is not None:
                    data = payload.get('body')
                    print('data', data)
                    deployment_dict['AWS_regions'][reg]['code_upload_time'] = data.get(bucket)
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')

    def deploy_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::Function deployment')
        print('AWS::Function deployment')
        if 'AWS_regions' in deployment_dict:
            responses = []
            for region in deployment_dict['AWS_regions']:
                bucket_name = deployment_dict['AWS_regions'][region]['bucket_name']
                role_arn = deployment_dict['aws_deployment_role']
                function_name = deployment_dict['function_name']
                handler_name = deployment_dict['aws_handler']
                code_package_key = deployment_dict['aws_code'].split('/')[-1]
                function_memory_list = deployment_dict['AWS_regions'][region]['memory_configurations']
                logging.info('deploying to %s: %s' % (region, str(function_memory_list)))
                runtime = deployment_dict['aws_runtime']
                function_timeout = deployment_dict.get('aws_function_timeout', 900)
                layers = deployment_dict['AWS_regions'][region].get('layers', [])

                response = self.__aws_deploy_from_s3_v2(function_name=function_name, role_arn=role_arn,
                                                 handler_name=handler_name,
                                                 code_package_key=code_package_key, function_timeout=function_timeout,
                                                 runtime=runtime,
                                                 function_memory_list=function_memory_list, s3_bucket_name=bucket_name,
                                                 s3_region=region, layers=layers)

                deployment_dict['AWS_regions'][region]['deployer_feedback'] = response
                responses.append(response)
            logging.info(responses)
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')
        return deployment_dict

    def delete_function(self, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::Function Deletion')
        if 'AWS_regions' in deployment_dict:
            pareto = kwargs.get('pareto', None)
            if pareto is not None:
                for p in pareto:
                    if p.get('provider') == 'AWS':
                        self.__delete_lambda_function(region=p.get('region'),
                                                      function_name=deployment_dict['function_name'],
                                                      function_memory_list=list(p.get('MB')))
            else:
                for region in deployment_dict['AWS_regions']:
                    self.__delete_lambda_function(region=region, function_name=deployment_dict['function_name'],
                                                  function_memory_list=deployment_dict['AWS_regions'][region][
                                                      'memory_configurations'])
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')

    def delete_storage(self, *, deployment_dict: Dict, **kwargs):
        logging.debug('AWS::Bucket Deletion')
        if 'AWS_regions' in deployment_dict:
            for region in deployment_dict['AWS_regions']:
                self.__delete_aws_bucket(region=region,
                                         bucket_name=deployment_dict['AWS_regions'][region]['bucket_name'])
        else:
            logging.info('Key \"AWS_regions\" not found in deployment_dict')

    def __iam_client(self):
        session = boto3.session.Session()
        return session.client('iam')

    def __lambda_client(self, region_name: str = 'us-east-1'):
        """Instantiate a thread-safe Lambda client"""
        session = boto3.session.Session()
        return session.client('lambda', region_name=region_name)

    def __s3_client(self, region_name: str = 'us-east-1'):
        session = boto3.session.Session()
        return session.client('s3', region_name=region_name)

    def __create_aws_bucket(self, *, region=None, bucket_name=None):
        bucket_client = self.__s3_client(region_name=region)

        if bucket_name is None:
            bucket_name = uuid.uuid4().hex
        retries = 3
        for counter in range(retries):
            try:
                if region == 'us-east-1':
                    bucket_client.create_bucket(Bucket=bucket_name, ACL='private')
                else:
                    bucket_client.create_bucket(Bucket=bucket_name, ACL='private',
                                                CreateBucketConfiguration={'LocationConstraint': region})
                return bucket_name
            except botocore.exceptions.ClientError as e:
                print(e)
                continue
        raise "Bucket creation retries limit reached"

    def __aws_deploy_single_from_bucket(self, *, function_name: str, role_arn: str, handler_name: str,
                                        code_package_key: str,
                                        s3_bucket_name: str, function_memory: int = 128, function_timeout: int = 3,
                                        runtime: str, deployment_package_type: str = 'Zip', deployment_region: str,
                                        layers: List = []):
        lam_client = self.__lambda_client(region_name=deployment_region)
        response = lam_client.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler_name,
            Code={
                'S3Bucket': s3_bucket_name,
                'S3Key': code_package_key
            },
            Description='This is an automatically generated test for ' + function_name + ' with ' + str(
                function_memory) + ' mb memory and a runtime of ' + str(function_timeout),
            Timeout=function_timeout,
            MemorySize=function_memory,
            PackageType=deployment_package_type,
            Layers=layers
        )
        return response

    def __aws_deploy_from_s3_v2(self, *, function_name: str, role_arn: str, handler_name: str, code_package_key: str,
                                s3_bucket_name: str, function_memory_list: List[int], function_timeout: int = 3,
                                runtime: str, deployment_package_type: str = 'Zip', s3_region: str, layers: List = [],
                                is_no_op: bool = False) -> List:
        mem_response = []
        try:
            for mem in function_memory_list:
                time_measures = {'deployment_timestamp_utc_start': datetime.datetime.now(timezone.utc)}
                deployment_start = perf_counter()
                if 128 <= mem <= 10240:
                    if is_no_op:
                        deployment_fun_name = function_name
                    else:
                        deployment_fun_name = function_name + '_' + str(mem) + 'MB'
                    response = self.__aws_deploy_single_from_bucket(
                        function_name=deployment_fun_name,
                        role_arn=role_arn,
                        handler_name=handler_name,
                        s3_bucket_name=s3_bucket_name,
                        function_memory=mem,
                        function_timeout=function_timeout,
                        runtime=runtime,
                        deployment_package_type=deployment_package_type,
                        code_package_key=code_package_key,
                        deployment_region=s3_region,
                        layers=layers
                    )
                    time_measures['deployment_time'] = round((perf_counter() - deployment_start) * 1000)
                    time_measures['deployment_timestamp_utc_end'] = datetime.datetime.now(timezone.utc)
                    response['TimeMeasures'] = time_measures
                    mem_response.append({mem: response})

        except botocore.exceptions.ClientError as e:
            print(e)
            logging.error(e)
        return mem_response

    def __delete_aws_bucket(self, *, region: str, bucket_name: str):
        buck = boto3.resource('s3').Bucket(bucket_name)
        buck.objects.all().delete()
        s3 = self.__s3_client(region_name=region)
        return s3.delete_bucket(Bucket=bucket_name)

    def __delete_lambda_function(self, *, region: str, function_name: str, function_memory_list: List):
        lam_client = self.__lambda_client(region_name=region)
        for mem in function_memory_list:
            deployment_fun_name = function_name + '_' + str(mem) + 'MB'
            lam_client.delete_function(FunctionName=deployment_fun_name)
