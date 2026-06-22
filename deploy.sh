TAG=$(git rev-parse --short HEAD)
ECR="154794777636.dkr.ecr.eu-central-2.amazonaws.com/intern-diego-van-overberghe-shared"

docker build -t $ECR:$TAG .
docker push $ECR:$TAG

sed "s|IMAGE_URI_PLACEHOLDER|$ECR:$TAG|g" template.yaml > template-deployed.yaml

sam deploy --resolve-image-repos --template-file template-deployed.yaml