### How to use
to use this example code fill in the blanks in pagerank_deployment_json

upload the testOps_no_op.zip and graph-pagerank-code.zip to an s3 bucket.
deploy igraph-layer-py38.zip as layer in all regions you plan on deploying for aws lambda. 
runtimes must be python3.8 (layer only includes code for 3.8 and therefore code must be fun with 3.8 too)

functions for both providers are insid the graph-pagerank-code.zip