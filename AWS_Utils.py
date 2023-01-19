import datetime
import json
import logging
from time import perf_counter
import boto3
from typing import Dict, List
import botocore.exceptions
import os
import uuid
from datetime import timezone


def iam_client():
    session = boto3.session.Session()
    return session.client('iam')


def lambda_client(region_name: str = 'us-east-1'):
    """Instantiate a thread-safe Lambda client"""
    session = boto3.session.Session()
    return session.client('lambda', region_name=region_name)


def s3_client(region_name: str = 'us-east-1'):
    session = boto3.session.Session()
    return session.client('s3', region_name=region_name)


def region_test(region_name: str) -> bool:
    # default_sts = boto3.client('sts')
    region_sts = boto3.client('sts', region_name=region_name)
    try:
        region_sts.get_caller_identity()
        return True
    except botocore.exceptions.EndpointConnectionError as e:
        print('caught exception:', e)
        # print(default_sts.get_caller_identity())
        raise e


def update_lambda_config(*, function_name: str, region_name: str, **kwargs) -> Dict:
    aws_lambda = lambda_client(region_name=region_name)

    config_args = {
        'FunctionName': function_name,
    }

    if 'timeout' in kwargs:
        config_args['Timeout'] = kwargs['timeout']

    if 'memory_size' in kwargs:
        config_args['MemorySize'] = kwargs['memory_size']
    response = aws_lambda.update_function_configuration(**config_args)
    return response


def get_lambda_config(*, function_name, region_name):
    """Gets current configuration parameters for a given Lambda function"""
    aws_lambda = lambda_client(region_name=region_name)
    try:
        response = aws_lambda.get_function_configuration(FunctionName=function_name)
        return response
    except botocore.exceptions.ClientError as e:
        print(e)
        raise e


def get_function_state(*, function_name, region_name) -> Dict:
    aws_lambda = lambda_client(region_name=region_name)
    response_query_status = aws_lambda.get_function(FunctionName=function_name)
    res = {'Status': response_query_status['Configuration']['State'],
           'LastUpdateStatus': response_query_status['Configuration']['LastUpdateStatus']}
    return res


def is_function_ready(*, function_name, region_name) -> bool:
    res = get_function_state(function_name=function_name, region_name=region_name)
    if res['Status'] == 'Active':
        return True
    return False


def wait_for_function_update(*, function_name, region):
    """boto3 built in way to wait for aws updates, function_updated_v2 queries the status api every 1 second"""
    start = perf_counter()
    update_complete_waiter = lambda_client(region_name=region).get_waiter('function_updated_v2')
    try:
        update_complete_waiter.wait(FunctionName=function_name)
    except botocore.exceptions.WaiterError as e:
        print(e)

    print('Update done', 'Time: ', (perf_counter() - start))


def wait_for_function_ready(*, function_name, region):
    """boto3 built in way to wait for aws active, function_active_v2 queries the status api every 1 second"""
    start = perf_counter()
    function_ready_waiter = lambda_client(region_name=region).get_waiter('function_active_v2')
    try:
        function_ready_waiter.wait(FunctionName=function_name)
    except botocore.exceptions.WaiterError as e:
        print(e)
    print('Function ready', function_name, 'Time: ', (perf_counter() - start))


def save_old_config(function_name: str, region_name):
    current_config = get_lambda_config(function_name=function_name, region_name=region_name)
    current_memory_size = current_config['MemorySize']
    current_timeout = current_config['Timeout']
    print(current_config)
    print(current_memory_size)
    print(current_timeout)
    return {'MemorySize': current_memory_size, 'Timeout': current_timeout}


def invoke_lambda(*, function_name: str, payload, invocation_type: str, log_type: str = 'None', region: str):
    """function to run a single lambda function"""
    aws_lambda = lambda_client(region_name=region)

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

    except (TypeError, json.decoder.JSONDecodeError):
        # logger.warning('Unable to parse Lambda Payload JSON response.')
        response['Payload'] = None

    return response


def invoker_timed(function_name: str, payload, execution_times: List, region: str, thread_id):
    res = {'execution_start_utc': datetime.datetime.now(timezone.utc)}
    start = perf_counter()

    invoke_lambda(function_name=function_name, payload=payload, invocation_type='RequestResponse', region=region)
    end = perf_counter()
    # append is thread safe
    res['execution_time'] = end - start
    res['execution_end_utc'] = datetime.datetime.now(timezone.utc)
    execution_times[thread_id] = res


# TODO this needs an error raised
def create_aws_bucket(region: str, bucket_name: str = None):
    bucket_client = s3_client(region_name=region)
    if bucket_name is None:
        bucket_name = uuid.uuid4().hex

    retries = 3

    for counter in range(retries):
        try:
            if region == 'us-east-1':
                bucket_client.create_bucket(Bucket=bucket_name, ACL='private')
            else:
                bucket_client.create_bucket(Bucket=bucket_name, ACL='private', CreateBucketConfiguration={'LocationConstraint': region})
            return bucket_name
        except botocore.exceptions.ClientError as e:
            print(e)
            continue
    raise "Bucket creation retries limit reached"


def aws_delete_bucket(region: str, bucket_name: str):
    buck = boto3.resource('s3').Bucket(bucket_name)
    buck.objects.all().delete()
    s3 = s3_client(region_name=region)
    return s3.aws_delete_bucket(Bucket=bucket_name)


def aws_deploy_from_s3_v2(*, function_name: str, role_arn: str, handler_name: str, code_package_key: str, s3_bucket_name: str, function_memory_list: List[int], function_timeout: int = 3, runtime: str, deployment_package_type: str = 'Zip', s3_region: str):
    total_response = {}
    created_buckets = []
    creation_regions = []
    try:
        mem_response = {}
        for mem in function_memory_list:
            time_measures = {'file_transfer_time': 0}
            deployment_start = perf_counter()
            time_measures['deployment_timestamp_utc_start'] = datetime.datetime.now(timezone.utc)
            if 128 <= mem <= 10240:
                deployment_fun_name = function_name + '_' + str(mem) + 'MB'
                response = __aws_deploy_single_from_bucket(
                    function_name=deployment_fun_name,
                    role_arn=role_arn,
                    handler_name=handler_name,
                    s3_bucket_name=s3_bucket_name,
                    function_memory=mem,
                    function_timeout=function_timeout,
                    runtime=runtime,
                    deployment_package_type=deployment_package_type,
                    code_package_key=code_package_key,
                    deployment_region=s3_region
                )
                time_measures['deployment_time'] = perf_counter() - deployment_start
                time_measures['deployment_timestamp_utc_end'] = datetime.datetime.now(timezone.utc)
                response['TimeMeasures'] = time_measures
                mem_response[mem] = response

            total_response[s3_region] = mem_response

    except botocore.exceptions.ClientError as e:
        print(e)

    finally:
        for counter in range(len(created_buckets)):
            aws_delete_bucket(creation_regions[counter], created_buckets[counter])
            print('Deleted bucket ', created_buckets[counter], 'in', creation_regions[counter])

    return total_response


#deprecated needs to be removed -> outsourced to pyStorage
def aws_deploy_from_s3(*, function_name: str, role_arn: str, handler_name: str, code_package_key: str, s3_bucket_name: str, function_memory_list: List[int], function_timeout: int = 3, runtime: str, deployment_package_type: str = 'Zip', deployment_regions: List[str], s3_region: str):
    total_response = {}
    created_buckets = []
    creation_regions = []
    sync_loc = 's3://' + s3_bucket_name + '/'
    try:
        for region in deployment_regions:
            if region == s3_region:
                mem_response = {}
                for mem in function_memory_list:
                    time_measures = {'file_transfer_time': 0}
                    deployment_start = perf_counter()
                    time_measures['deployment_timestamp_utc_start'] = datetime.datetime.now(timezone.utc)
                    if 128 <= mem <= 10240:
                        deployment_fun_name = function_name + '_' + str(mem) + 'MB'
                        response = __aws_deploy_single_from_bucket(
                            function_name=deployment_fun_name,
                            role_arn=role_arn,
                            handler_name=handler_name,
                            s3_bucket_name=s3_bucket_name,
                            function_memory=mem,
                            function_timeout=function_timeout,
                            runtime=runtime,
                            deployment_package_type=deployment_package_type,
                            code_package_key=code_package_key,
                            deployment_region=region
                        )
                        time_measures['deployment_time'] = perf_counter() - deployment_start
                        time_measures['deployment_timestamp_utc_end'] = datetime.datetime.now(timezone.utc)
                        response['TimeMeasures'] = time_measures
                        mem_response[mem] = response

                    total_response[region] = mem_response
            else:
                s3_start = perf_counter()
                created_buckets.append(create_aws_bucket(region))
                creation_regions.append(region)
                target_loc = 's3://' + created_buckets[-1] + '/'
                print(target_loc)
                sync_command = f"aws s3 sync " + sync_loc + f" " + target_loc + f" --exclude \"*\" --include \"deployment/*\""
                print(sync_command)
                os.system(sync_command)
                s3_end = perf_counter()
                mem_response = {}
                for mem in function_memory_list:
                    time_measures = {'file_transfer_time': (s3_end - s3_start)}
                    deployment_start = perf_counter()
                    time_measures['deployment_timestamp_utc_start'] = datetime.datetime.now(timezone.utc)
                    if 128 <= mem <= 10240:
                        deployment_fun_name = function_name + '_' + str(mem) + 'MB'
                        response = __aws_deploy_single_from_bucket(
                            function_name=deployment_fun_name,
                            role_arn=role_arn,
                            handler_name=handler_name,
                            s3_bucket_name=created_buckets[-1],
                            function_memory=mem,
                            function_timeout=function_timeout,
                            runtime=runtime,
                            deployment_package_type=deployment_package_type,
                            code_package_key=code_package_key,
                            deployment_region=region
                        )
                        time_measures['deployment_time'] = perf_counter() - deployment_start
                        time_measures['deployment_timestamp_utc_end'] = datetime.datetime.now(timezone.utc)
                        response['TimeMeasures'] = time_measures
                        mem_response[mem] = response
                    total_response[region] = mem_response
    except botocore.exceptions.ClientError as e:
        print(e)

    finally:
        for counter in range(len(created_buckets)):
            aws_delete_bucket(creation_regions[counter], created_buckets[counter])
            print('Deleted bucket ', created_buckets[counter], 'in', creation_regions[counter])

    return total_response


def aws_pre_deploy(*, bucket_name: str, zip_file: str, region):
    pass


def __aws_deploy_single_from_bucket(*, function_name: str, role_arn: str, handler_name: str, code_package_key: str, s3_bucket_name:str, function_memory: int = 128, function_timeout: int = 3, runtime: str, deployment_package_type: str = 'Zip', deployment_region: str):
    lam_client = lambda_client(region_name=deployment_region)
    response = lam_client.create_function(
        FunctionName=function_name,
        Runtime=runtime,
        Role=role_arn,
        Handler=handler_name,
        Code={
            'S3Bucket': s3_bucket_name,
            'S3Key': code_package_key
        },
        Description='This is an automatically generated test for ' + function_name + ' with ' + str(function_memory) + ' mb memory and a runtime of ' + str(function_timeout),
        Timeout=function_timeout,
        MemorySize=function_memory,
        PackageType=deployment_package_type
    )
    return response


def upload_to_aws_bucket(*, filename: str, bucket: str, object_name=None):
    s3 = s3_client()
    if object_name is None:
        object_name = os.path.basename(filename)

    try:
        response = s3.upload_file(filename, bucket, object_name)
    except botocore.exceptions.ClientError as e:
        logging.error(e)
        return False
    return True