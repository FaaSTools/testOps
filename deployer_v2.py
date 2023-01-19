from Gen_Utils import *

from deployer import *
from typing import Union, List
import logging


def deploy_function(deployment_info_json: Union[dict, str], *, deploy_no_op:bool = True) -> Dict:
    """Function to deploy FaaS functions, takes either a dictionary or a string to a json with deployment dict format

    :param deployment_info_json:
    :return: deployment_dict: Dict
    """

    create_credentials()
    deployment_dict = {}
    deployer_list: List[DeployerInterface] = []

    if type(deployment_info_json) == str:
        if not exists(deployment_info_json):
            logging.error('FILE NOT FOUND ERROR:: %s' % deployment_info_json)
            raise 'FILE NOT FOUND ERROR'
        else:
            with open(deployment_info_json, 'r') as f:
                deployment_dict = json.load(f)
    else:
        deployment_dict = deployment_info_json

    aws = AWSDeployer()
    gcp = GCPDeployer()
    deployer_list.append(aws)
    deployer_list.append(gcp)

    for deployer in deployer_list:
        deployer.create_storage(deployment_dict=deployment_dict)
        deployer.upload_function(deployment_dict=deployment_dict)
        if deploy_no_op:
            deployer.upload_function(deployment_dict=deployment_dict, is_no_op=True)
            deployer.deploy_no_op(deployment_dict=deployment_dict)
        deployer.deploy_function(deployment_dict=deployment_dict)
        deployer.delete_storage(deployment_dict=deployment_dict)

    return deployment_dict


def delete_function(deployment_dict: dict, **kwargs):
    deployer_list: List[DeployerInterface] = []
    aws = AWSDeployer()
    gcp = GCPDeployer()
    deployer_list.append(aws)
    deployer_list.append(gcp)

    # needs provider specific stuff
    region = kwargs.get('region', None)
    if region is not None:
        print('region not none', region)
        for deployer in deployer_list:
            deployer.delete_function(deployment_dict=deployment_dict, region=region, mem_list=kwargs.get('mem_list'))
    else:
        for deployer in deployer_list:
            deployer.delete_function(deployment_dict=deployment_dict)

# deploy_function('py_copy_scenario3.json')
