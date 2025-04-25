#!/bin/bash
# Service scaling script for TerraFusion Platform
# This script manages scaling of services in Docker Compose or Docker Swarm

set -e

# Configuration
SERVICE=${1:-"web"}  # Default to web service if not provided
REPLICAS=${2:-1}     # Default to 1 replica if not provided
ENV=${3:-"prod"}     # Default to production environment if not provided

# Check if we're running in Swarm mode
SWARM_MODE=$(docker info --format '{{.Swarm.LocalNodeState}}')

echo "Scaling TerraFusion service: $SERVICE"
echo "Environment: $ENV"

# For Docker Swarm mode
if [ "$SWARM_MODE" == "active" ]; then
    echo "Running in Docker Swarm mode"
    echo "Scaling service to $REPLICAS replicas..."
    
    # Scale the service
    docker service scale terrafusion_${SERVICE}=$REPLICAS
    
    # Check current status
    echo "Current service status:"
    docker service ps terrafusion_${SERVICE}
    
    echo "Scaling complete"

# For Docker Compose
else
    echo "Running in Docker Compose mode"
    echo "Scaling service to $REPLICAS replicas..."
    
    # Scale the service using docker-compose
    docker-compose -f docker-compose.yml -f docker-compose.${ENV}.yml up -d --scale ${SERVICE}=${REPLICAS}
    
    # Check current status
    echo "Current container status:"
    docker-compose ps ${SERVICE}
    
    echo "Scaling complete"
fi

# Simple monitoring after scaling
echo "Monitoring service health for 30 seconds..."
for i in {1..6}; do
    echo "Check $i of 6..."
    curl -s http://localhost:5000/health || echo "Service not responding"
    sleep 5
done

echo "Scaling operation completed successfully"