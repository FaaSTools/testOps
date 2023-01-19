from Gen_Utils import *

from invoker import *
from typing import Union, List, Dict
import logging


def run_experiment(deployment_info_json: Union[dict, str]) -> Dict:
    deployment_dict = {}
    deployer_list: List[InvokerInterface] = []

    if type(deployment_info_json) == str:
        if not exists(deployment_info_json):
            logging.error('FILE NOT FOUND ERROR:: %s' % deployment_info_json)
            raise 'FILE NOT FOUND ERROR'
        else:
            with open(deployment_info_json, 'r') as f:
                deployment_dict = json.load(f)
    else:
        deployment_dict = deployment_info_json

    invoker_list = []
    aws = AWSInvoker()
    gcp = GCPInvoker(gcp_project_id=deployment_dict['gcp_project_id'])

    invoker_list.append(aws)
    invoker_list.append(gcp)

    payload = deployment_dict.get('payload')

    for invoker in invoker_list:
        invoker.run_experiment(deployment_dict=deployment_dict, payload=payload,
                               repetitions_of_experiment=deployment_dict.get('repetitions_of_experiment', 1),
                               repetitions_per_function=deployment_dict.get('repetitions_per_function', 2),
                               concurrency=deployment_dict.get('concurrency', 1))

    result_filename = deployment_dict['function_name'] + '_result.json'
    export_json_to_file(result_filename, deployment_dict)
    return deployment_dict


#deployment_info_json = 'py_copy_scenario3.json'

#deployment_dict = None

#with open(deployment_info_json, 'r') as f:
#    deployment_dict = json.load(f)

#for p in deployment_dict['payload']:

#    p.update({'aws_access_key_id': 'ASIARLNDGQNPTKATROHC'})
#    p.update({"aws_secret_key": "zeR5I5NNCFw59IU6zcw3Noo+EzdWxAVINUtG45Ia"})
#    p.update({"aws_session_token": 'FwoGZXIvYXdzEEEaDBwbViKOBcb208NUpCLNAfy76W4I0JSaj8d8Ct2EVpfwZfba1ebXR+VELa84XYySIZ5n49woqADj+xObqmASSFSuK7Pr5ZK1jIdKv5LLJEPwU35uXgKXKW7yKlYl+f/lGglQVjheIf0L5xsTd/NP7sAK53ruqXYNtubEByom/QnC0Fq19Elv2aqLno0FkV+QX9jatT7I8fFZXcnVQNXuJWnOPUrdqbvIwFVbisEPKOZnW6qYC9oiHIYwRaRAxSREsuULR75w1km9bXG9ApqvrdIvsAwqiZL1qZiJgOko/tDLnAYyLThowAYx5wugt47O60dbr6el6LOmHIxDWSSfuFDWkih/dAQM3/2t4My3nYNkMA=='})
#    p.update({ "client_email": "faas-355708@appspot.gserviceaccount.com"})
#    p.update({"private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQD12ON75x4aS6Wa\nzlRiHV5NcpysqG7BfgbTZWpKt6A3u+7ZLU96fdb6F0zt6Ya0uAectkvBdqqB15D4\n8sDer0o7rGAdHY9nNs2qQeAEk/3yde6KHtEZgSp2VOoxuzm+kbk2gQfcLMS+n3sT\nLA+4wUa93Q+/7UiV/Wt6CcWWu9xeEanUivJWhOk3rBmqSdkRkOSXLqO08VJWFK6I\nxgv6ohH/OmAzyoqmoriF+gzz/A6M2M9zQ9V4q0aICkNcnPNeXBxEAXxh8dl1bc1D\nA1/FpadKsnUTwAAC/F0QDGSME1KHlHBsiMJBh7wnCEk8QreiHj9vxNVhYFcWCWkU\nhOsBCASfAgMBAAECggEANsLW+RRkCitree4Xsbsk9E9hQrxJ32O5FYFzia0ZTRDZ\nhRqop3o8Vny2MBBiZwLO/0ND4JYUKNPhgPJhr7iP6nbc+d9JwA3fBduikKJ+YHGQ\nbseqf+nbkXwcpnMzy5UeElvvakW2lVdkzMJ1xguXPFdvWKr8Dhziwc5Haunxjiol\nTORwpR2c9IfLgPe93Kt6UhhUSq83oMlHqjTFhl1e/HoZtXZIr3T0m34E48/WyHdO\n6SXDXV8BT9sPsFOsQGbyGeL+Q0OYvtxwuoVDe8fe0ntC6+dTYVVBgQ/cqfUEMbbo\n8ASF8LCL5xvFvM+XO8lS/Zd6gRpQH/QovYbd1CAU4QKBgQD7bRAiXnQYq5REkp1t\nPUwQfWV0hOLno4dIBls4V0Tg87zX2nqOxEfR+YFHBbjEVwjnMA5wfXtBqgsDqklM\n0Y2les0okm7peWlhWW+A3+YI+CNcUCHjSUr78rhB7CztqcX44IRFa89jePstZ8wE\nZZ8ap9GgeV8QUXY0h61af1kUOQKBgQD6UdgUlIXsUqE/vKvqZsgXKxnGpsm838fu\nCqtdxZ1sE27VaZ8kSw4fvtN3TKHfRDDKaDvxteBSDGR6dID0hEM/z75xg16r5i5O\nZh9/VugDJu0jgt40JIzRe9zAJFeknesuOjxuJybaGz11v2V6dqxo4Jkr/MoDs/r5\nmPMAyzvPlwKBgG8ZJzr4n7ZTAuY2HwgpQNY8grs1CQqwMNP7sw03SsFYEocTDHrP\ncqju5lgayCVCDDYT/x1n5TID0HAjK9ac9kk79THLWuUh+BXDLkk1JnGqK/3bjs3f\nEho4i4DdupCeJ1Os6eW/GNnsmJjct8LtoJtnsnKFjyMny+K0XT6S7SrJAoGATLrz\nynMwjh1SElCKPiLdaMSsdQlBQ6UxCtW4a9kchTl7uu1Se/SJ0s9S0PnrkJ29ev3y\niggfR+dGkYbO1KUKXDAZB4Cmb3jybtO9CfKg0f6HqGAALumZRMl8BGXfe7Vwls4B\nIh7cOPUqpMJTn/NqrAdUzHgDkJkF8Kairnad0ecCgYAl5lOThNQ8sJq8/HgvoRq9\nhizdsFOOn4y8oC1SwNFYmN1CdlEzzUQ3JZw+u/87V6kqFVBrz0EPDrXR6QinxpBL\n+vs2owloHWo5BjchDcTaSRxCDNNwdDXLN1SiZaqh6eLIGGMU5SsVCdheLSHo5B8N\n9R3nMaIMVnfsP+Lvqcr8Sw==\n-----END PRIVATE KEY-----\n"})
#    p.update({"project_id": "faas-355708"})
#    print(p)

#run_experiment(deployment_dict)
#run_experiment('py_copy_scenario2.json')

