#!/bin/bash
# Deployment script for TerraFusion Platform
# This script handles deployment to various environments

set -e

# Configuration
ENV=${1:-"dev"}  # Default to dev environment if not provided
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"terrafusion"}
VERSION=${VERSION:-"latest"}

# Determine if we're using Docker Compose or Kubernetes
DEPLOY_TYPE=${2:-"compose"}  # Default to docker-compose

echo "Deploying TerraFusion Platform"
echo "Environment: $ENV"
echo "Deployment type: $DEPLOY_TYPE"

# Build the Docker image
echo "Building Docker image..."
docker build -t ${DOCKER_REGISTRY}/terrafusion:${VERSION} .

# Push the Docker image if we're using Kubernetes
if [ "$DEPLOY_TYPE" == "k8s" ]; then
    echo "Pushing Docker image to registry..."
    docker push ${DOCKER_REGISTRY}/terrafusion:${VERSION}
fi

# Deploy based on deployment type
if [ "$DEPLOY_TYPE" == "compose" ]; then
    echo "Deploying with Docker Compose..."
    
    # Ensure .env file exists
    if [ ! -f .env ]; then
        echo "Error: .env file not found"
        echo "Please create a .env file with required environment variables"
        exit 1
    fi
    
    # Deploy with Docker Compose
    docker-compose -f docker-compose.yml -f docker-compose.${ENV}.yml up -d
    
    echo "Deployment completed with Docker Compose"
    
elif [ "$DEPLOY_TYPE" == "k8s" ]; then
    echo "Deploying with Kubernetes..."
    
    # Check for kubectl
    if ! command -v kubectl &> /dev/null; then
        echo "Error: kubectl not found"
        echo "Please install kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl/"
        exit 1
    fi
    
    # Create namespace if it doesn't exist
    NAMESPACE="terrafusion-${ENV}"
    if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
        echo "Creating namespace: ${NAMESPACE}"
        kubectl create namespace ${NAMESPACE}
    fi
    
    # Apply Kubernetes manifests
    echo "Applying Kubernetes manifests for ${ENV} environment..."
    
    # Check for kustomize
    if command -v kustomize &> /dev/null; then
        echo "Using kustomize..."
        kustomize build k8s/overlays/${ENV} | kubectl apply -f -
    else
        echo "Using kubectl apply -k..."
        kubectl apply -k k8s/overlays/${ENV}
    fi
    
    echo "Kubernetes deployment completed"
    
    # Wait for deployment to complete
    echo "Waiting for deployment to complete..."
    kubectl rollout status deployment/terrafusion-api -n ${NAMESPACE}
    
    # Display service information
    echo "Service information:"
    kubectl get svc -n ${NAMESPACE}
    
    # Display ingress information if it exists
    if kubectl get ingress -n ${NAMESPACE} &> /dev/null; then
        echo "Ingress information:"
        kubectl get ingress -n ${NAMESPACE}
    fi
    
else
    echo "Error: Unknown deployment type: $DEPLOY_TYPE"
    echo "Supported types: compose, k8s"
    exit 1
fi

echo "Deployment completed successfully"