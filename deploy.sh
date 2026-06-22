#!/usr/bin/env bash
set -euo pipefail

TAG=$(git rev-parse --short HEAD)
ECR="154794777636.dkr.ecr.eu-central-2.amazonaws.com/intern-diego-van-overberghe-shared"

aws ecr get-login-password --region eu-central-2 | docker login --username AWS --password-stdin 154794777636.dkr.ecr.eu-central-2.amazonaws.com

docker build -t intern-diego-van-overberghe-shared:$TAG .
docker tag intern-diego-van-overberghe-shared:$TAG $ECR:$TAG
docker push $ECR:$TAG

sed "s|IMAGE_URI_PLACEHOLDER|$ECR:$TAG|g" template.yaml > template-deployed.yaml

sam deploy --resolve-image-repos --capabilities CAPABILITY_NAMED_IAM --template-file template-deployed.yaml

rm template-deployed.yaml