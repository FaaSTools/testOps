# testOps

testOps is a tool to deploy, time and analyse FaaS functions
currently AWS and GCP are supported



## dependencies

- python3.9+
- virtualenv installed
- lockfile for usage with venv is supplied

## installation
- create virtualenviroment
- navigate to venv\Scripts and run activate (depending on shell and os)
- then use pipenv sync to install dependencies (in testOps root folder)

## usage

python testops.py [-h] [-d] [-i] [-a] [-keep {all,none,pareto}]  filename

- -h displays help
- -d or --deploy activates the deployer functionality
- -i or --invoke activates the invoker and timing functionality
- -a or --analyse activates the analyser functionality
- -keep pick all, none or pareto to declare which functions should be kept after the run is finished, the pareto option requires -a (the analyser) to be active. if this option is ignores -keep all is used
- filename the filename of the input json

## requirements
- testops requires a deployed pyStorage function on AWS
- testops requires a credentials.json which holds the credentials for AWS / GCP

## example credentials json
{  
  "amazon":  
  {  
    "aws_access_key_id": "xyz",  
    "aws_secret_access_key": "xyz",  
    "aws_session_token": "xyz"  
  },  
  "google":  
  {  
    "client_email": "xyz@appspot.gserviceaccount.com",  
    "private_key":"-----BEGIN PRIVATE KEY-----\xyz\n-----END PRIVATE KEY-----\n",  
    "project_id": "xyz"  
  }  
}  

## example input json

{  
	"function_name": "function_name",  
	"aws_code": "s3://xyz.zip",  
	"gcp_code": "s3://xyz.zip",  
	"no_op_code": "s3://xyz.zip",  
	"aws_handler": "lambda_function.lambda_handler",  
	"gcp_handler":  "entry_handler",  
	"no_op_handler_aws": "lambda_function.lambda_handler",  
	"no_op_handler_gcp":  "entry_handler",  
	"gcp_project_id": "xyz",    
	"aws_deployment_role" : "arn:/LabRole",  
	"pyStorage_arn": "arn::function:pyStorage",  
	"aws_runtime": "python3.9",  
	"gcp_runtime": "python39",  
	"file_type": "zip",  
	"repetitions_of_experiment": 2,  
    "repetitions_per_function": 6,  
    "concurrency": 3,  
	"payload": [{"input": 25}],  
	"AWS_regions": {  
		"us-west-2": {  
			"memory_configurations":[  
				128  
		]},  
		"us-east-1":{  
			"memory_configurations" :[  
				226  
		]}
	},
	"GCP_regions": {  
		"us-west2": {  
			"memory_configurations": [  
				128  
			]}  
	}
}
## aws layer creator for python

small bonus, in folder aws layer creator you can find a docker script to create an AWS layer out of a requirement.txt
refer to readme in the folder