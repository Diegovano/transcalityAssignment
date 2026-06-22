Usage Guide:

Follow AWS Setup instructions from the `intern_assignment.md`

run `deploy.sh` to build the image, upload it to ECR, deploy the lambdas and the state machine.

run `aws stepfunctions start-execution \`
    `--state-machine-arn arn:aws:states:eu-central-2:154794777636:stateMachine:intern-diego-van-overberghe-pipeline \`
    `--input '{"scenario_zip_url": "s3://transcality-intern/shared/small-scenario.zip", "output_prefix": "s3://transcality-intern/diego-van-overberghe/run-n"}'`

In the output of the previous command, locate the execution ARN. Copy this and use it to query the state of the execution:

run `aws stepfunctions describe-execution --execution-arn arn:aws:states:eu-central.....`

To tear down, run `sam delete --stack-name intern-diego-van-overberghe-pipeline-stack`

Assumptions:

You are happy me not checking GPG keys during the sumo-builder installation of sumo

You do not mind me leaving infrastructure which was useful during developement. For example allowing sumo_sim handler to discriminate s3 uris vs paths. My thinking here is that the flexibility allows easier integration into an offline testing pipeline, saving AWS credits (I have no idea how much this stuff costs tbh).

Assuming sumo only produces summary.xml and edge.xml. Other files not cleared during the `finally` step.

Assuming that top 10 busiest does not need to be sorted

I struggled with running `sam build`, then `sam deploy`, as `sam build` was saying that docker was not running even though it was. I therefore decided to build the image myself and upload it to ECR. The deploy script handles setting the URI of the image identically on each deploy. As a result, all three functions share the same repo.

The `deploy.sh` script is idempotent only if changes are committed. This is because of how images are tagged with a commit hash rather than something like a timestamp, or uuid, which would be essentially unique on each deploy. Without a new commit, `sam` will say "no changes to deploy". 

I am retrying on any `States.ALL` failure, not just `States.TaskFailure`, so more errors are caught. Its a superset of TaskFailed, so I hope it is fine.

What I would do with more time:

If I had more time I would make the Dockerfile a little more extentible. Specifically, to add more sumo-tools for instance, we first need to check if its a dynamic executable, in which case we need to copy libs. Otherwise copying the executable is enough.