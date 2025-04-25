#!/bin/bash
# Deployment script for TerraFusion Platform
# This script deploys the application to a production environment

set -e

# Configuration
ENV=$1
DOCKER_REGISTRY="terrafusion"
APP_NAME="terrafusion"
GIT_BRANCH="main"

# Check if environment is provided
if [ -z "$ENV" ]; then
    echo "Error: No environment provided"
    echo "Usage: $0 <environment> (dev|staging|prod)"
    exit 1
fi

if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "Error: Invalid environment. Use dev, staging, or prod"
    exit 1
fi

echo "Starting deployment to $ENV environment"

# Pull latest code from repository
echo "Pulling latest code from $GIT_BRANCH branch"
git checkout $GIT_BRANCH
git pull origin $GIT_BRANCH

# Build Docker image with environment-specific tag
echo "Building Docker image for $ENV environment"
docker-compose build
docker tag ${DOCKER_REGISTRY}/api:latest ${DOCKER_REGISTRY}/api:${ENV}

# Push image to registry
echo "Pushing Docker image to registry"
docker push ${DOCKER_REGISTRY}/api:${ENV}

# Deploy to environment
echo "Deploying to $ENV environment"
if [ "$ENV" == "prod" ]; then
    # For production, we want to be extra careful
    echo "Production deployment - additional safeguards in place"
    
    # Take backup before deployment
    echo "Taking database backup before deployment"
    ./scripts/backup.sh
    
    # Deploy with zero-downtime
    echo "Performing zero-downtime deployment"
    # Implementation depends on your infrastructure (Kubernetes, Swarm, etc.)
    # Example for docker-compose:
    docker-compose -f docker-compose.yml -f docker-compose.${ENV}.yml up -d --scale web=2 --no-recreate web
    sleep 10
    docker-compose -f docker-compose.yml -f docker-compose.${ENV}.yml up -d --force-recreate --scale web=2 web
else
    # For non-production environments, simpler deployment
    docker-compose -f docker-compose.yml -f docker-compose.${ENV}.yml up -d
fi

echo "Deployment to $ENV environment completed successfully"