#!/bin/bash
set -e

# TerraFusion Platform Deployment Script
# This script handles deployment to dev, staging, and production environments

# Usage: ./deploy.sh [dev|staging|prod]

# Default to dev if no environment specified
ENVIRONMENT=${1:-dev}
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DOCKER_REGISTRY="terrafusion"
IMAGE_NAME="terrafusion"

echo "🚀 Starting TerraFusion Platform deployment to $ENVIRONMENT environment"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "❌ Invalid environment: $ENVIRONMENT"
  echo "Usage: ./deploy.sh [dev|staging|prod]"
  exit 1
fi

# Set tag based on environment
if [ "$ENVIRONMENT" == "prod" ]; then
  TAG="latest"
else
  TAG="$ENVIRONMENT"
fi

# Build Docker image
echo "🔨 Building Docker image: $DOCKER_REGISTRY/$IMAGE_NAME:$TAG"
docker build -t $DOCKER_REGISTRY/$IMAGE_NAME:$TAG .

# Push image to registry
echo "⬆️ Pushing image to registry"
docker push $DOCKER_REGISTRY/$IMAGE_NAME:$TAG

# Deploy to environment
echo "📦 Deploying to $ENVIRONMENT environment"
if [ "$ENVIRONMENT" == "dev" ]; then
  # Deploy to development environment
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
elif [ "$ENVIRONMENT" == "staging" ]; then
  # Deploy to staging environment using Docker Swarm or Kubernetes
  if command -v kubectl &> /dev/null; then
    echo "🔄 Deploying to Kubernetes staging environment"
    kubectl apply -k k8s/overlays/staging/
    kubectl rollout status deployment/terrafusion-api -n terrafusion-staging
  else
    echo "🔄 Deploying to Docker Swarm staging environment"
    docker stack deploy -c docker-compose.yml -c docker-compose.staging.yml terrafusion-staging
  fi
elif [ "$ENVIRONMENT" == "prod" ]; then
  # Deploy to production environment using Kubernetes
  if command -v kubectl &> /dev/null; then
    echo "🔄 Deploying to Kubernetes production environment"
    kubectl apply -k k8s/overlays/prod/
    kubectl rollout status deployment/terrafusion-api -n terrafusion-prod
  else
    echo "❌ Production deployment requires Kubernetes. Please install kubectl."
    exit 1
  fi
fi

# Run database migrations
echo "📊 Running database migrations"
if [ "$ENVIRONMENT" == "dev" ]; then
  # Run local migrations
  docker-compose exec web flask db upgrade
else
  # Run migrations in the deployed environment
  if command -v kubectl &> /dev/null; then
    PODS=$(kubectl get pods -n terrafusion-$ENVIRONMENT -l app=terrafusion-api -o jsonpath="{.items[0].metadata.name}")
    kubectl exec -it $PODS -n terrafusion-$ENVIRONMENT -- flask db upgrade
  else
    # Fallback for Docker Swarm
    docker exec $(docker ps -q -f name=terrafusion_web) flask db upgrade
  fi
fi

echo "✅ Deployment to $ENVIRONMENT completed successfully!"

# Run smoke tests
echo "🔍 Running smoke tests"
ENDPOINT=""
if [ "$ENVIRONMENT" == "dev" ]; then
  ENDPOINT="http://localhost:5000"
elif [ "$ENVIRONMENT" == "staging" ]; then
  ENDPOINT="https://staging.terrafusion.example.com"
elif [ "$ENVIRONMENT" == "prod" ]; then
  ENDPOINT="https://terrafusion.example.com"
fi

# Simple curl test to check if the API is responding
curl -s -o /dev/null -w "%{http_code}" $ENDPOINT/health | grep 200 > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ Health check passed!"
else
  echo "❌ Health check failed!"
  echo "Please check the deployment logs for more information."
  exit 1
fi

echo "🎉 TerraFusion Platform deployed to $ENVIRONMENT successfully!"