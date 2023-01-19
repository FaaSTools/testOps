import json
import os
import sys
from typing import Dict, List
from os.path import exists


def export_json_to_file(filename: str, json_data: Dict):
    f = open(filename, 'w')
    f.write(json.dumps(json_data, indent=4, default=str))
    f.close()


def print_neat_dict(dict):
    print(json.dumps(dict, indent=4, default=str))


def create_credentials():
    if not exists('credentials.json'):
        sys.exit('credentials.json not found!')

    else:
        with open('credentials.json', 'r') as cred:
            cred_json = json.load(cred)

            os.environ['AWS_ACCESS_KEY_ID'] = cred_json['amazon']['aws_access_key_id']
            os.environ['AWS_SECRET_ACCESS_KEY'] = cred_json['amazon']['aws_secret_access_key']
            os.environ['AWS_SESSION_TOKEN'] = cred_json['amazon']['aws_session_token']
            os.environ['GCP_client_email'] = cred_json['google']['client_email']
            os.environ['GCP_private_key'] = cred_json['google']['private_key']
            os.environ['GCP_project_id'] = cred_json['google']['project_id']
        cred.close()
