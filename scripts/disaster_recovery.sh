#!/bin/bash
set -e

# TerraFusion Platform Disaster Recovery Script
# This script automates the disaster recovery process
# Usage: ./disaster_recovery.sh [dev|staging|prod]

# Default to prod if no environment specified
ENVIRONMENT=${1:-prod}
TIMESTAMP=$(date +%Y%m%d%H%M%S)
S3_BUCKET="s3://terrafusion-backups"
S3_PREFIX="${ENVIRONMENT}"
LOG_FILE="disaster_recovery_${TIMESTAMP}.log"

# Start logging
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "🚨 STARTING TERRAFUSION DISASTER RECOVERY PROCEDURE 🚨"
echo "📅 Date: $(date)"
echo "🌐 Environment: ${ENVIRONMENT}"
echo "⏱️ Timestamp: ${TIMESTAMP}"
echo "📝 Log file: ${LOG_FILE}"
echo "----------------------------------------"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "❌ Invalid environment: $ENVIRONMENT"
  echo "Usage: ./disaster_recovery.sh [dev|staging|prod]"
  exit 1
fi

# Load environment variables from configuration file
if [ -f ".env.${ENVIRONMENT}" ]; then
    echo "📋 Loading environment variables from .env.${ENVIRONMENT}"
    source ".env.${ENVIRONMENT}"
else
    echo "⚠️ Warning: Environment file .env.${ENVIRONMENT} not found. Using existing environment variables."
fi

# Step 1: Find the latest backup
echo "🔍 Step 1: Finding the latest backup in S3..."
LATEST_BACKUP=$(aws s3 ls "${S3_BUCKET}/${S3_PREFIX}/" | grep "terrafusion_backup_" | sort -r | head -1 | awk '{print $4}')

if [ -z "${LATEST_BACKUP}" ]; then
    echo "❌ No backups found in S3 bucket: ${S3_BUCKET}/${S3_PREFIX}/"
    exit 1
fi

echo "✅ Latest backup found: ${LATEST_BACKUP}"
echo "📅 Backup date: $(echo $LATEST_BACKUP | grep -oP 'terrafusion_backup_\K\d{14}' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')"

# Step 2: Confirm recovery
echo "⚠️ WARNING: This will perform a full disaster recovery procedure."
echo "⚠️ All current data and infrastructure will be replaced with the backup data."
echo "⚠️ Environment: ${ENVIRONMENT}"
echo -n "Are you sure you want to proceed with disaster recovery? [y/N] "
read -r confirmation
if [[ ! "${confirmation}" =~ ^[Yy]$ ]]; then
    echo "❌ Disaster recovery cancelled"
    exit 1
fi

# Step 3: Restore database
echo "🔄 Step 3: Restoring database from backup..."
./restore.sh "${ENVIRONMENT}" "${LATEST_BACKUP}"
echo "✅ Database restore completed"

# Step 4: Provision infrastructure (if using Kubernetes)
if command -v kubectl &> /dev/null; then
    echo "🏗️ Step 4: Provisioning infrastructure using Kubernetes..."
    
    # Check if we can access the cluster
    if ! kubectl cluster-info &> /dev/null; then
        echo "⚠️ Cannot access Kubernetes cluster. Attempting to update kubeconfig..."
        # Try to update kubeconfig (AWS example)
        if command -v aws &> /dev/null; then
            aws eks update-kubeconfig --name terrafusion-cluster --region "${AWS_REGION:-us-east-1}"
        else
            echo "❌ Cannot access Kubernetes cluster and AWS CLI not available to configure access"
            exit 1
        fi
    fi
    
    # Create namespace if it doesn't exist
    NAMESPACE="terrafusion-${ENVIRONMENT}"
    kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply all Kubernetes manifests
    kubectl apply -k "k8s/overlays/${ENVIRONMENT}/" --prune -l app=terrafusion
    
    # Wait for resources to become ready
    kubectl rollout status deployment/terrafusion-api -n "${NAMESPACE}"
    
    echo "✅ Infrastructure provisioning completed"
else
    echo "⚠️ Kubernetes not available. Using Docker Compose for infrastructure..."
    
    # Deploy using Docker Compose
    if [ "${ENVIRONMENT}" == "prod" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    elif [ "${ENVIRONMENT}" == "staging" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
    else
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    fi
    
    echo "✅ Infrastructure provisioning completed using Docker Compose"
fi

# Step 5: Run database migrations
echo "🔄 Step 5: Running database migrations..."
if command -v kubectl &> /dev/null; then
    # If using Kubernetes
    NAMESPACE="terrafusion-${ENVIRONMENT}"
    POD=$(kubectl get pods -n "${NAMESPACE}" -l app=terrafusion,component=api -o jsonpath="{.items[0].metadata.name}")
    kubectl exec -n "${NAMESPACE}" "${POD}" -- flask db upgrade
else
    # If using Docker Compose
    docker-compose exec web flask db upgrade
fi
echo "✅ Database migrations completed"

# Step 6: Verify recovery
echo "🔍 Step 6: Verifying recovery..."
if command -v kubectl &> /dev/null; then
    # If using Kubernetes
    NAMESPACE="terrafusion-${ENVIRONMENT}"
    
    # Check deployment status
    READY_REPLICAS=$(kubectl get deployment terrafusion-api -n "${NAMESPACE}" -o jsonpath="{.status.readyReplicas}")
    TOTAL_REPLICAS=$(kubectl get deployment terrafusion-api -n "${NAMESPACE}" -o jsonpath="{.status.replicas}")
    
    if [ "${READY_REPLICAS}" == "${TOTAL_REPLICAS}" ]; then
        echo "✅ Deployment is healthy: ${READY_REPLICAS}/${TOTAL_REPLICAS} replicas ready"
    else
        echo "⚠️ Warning: Deployment not fully ready. ${READY_REPLICAS}/${TOTAL_REPLICAS} replicas ready"
    fi
    
    # Check service status
    SERVICE_IP=$(kubectl get svc -n "${NAMESPACE}" terrafusion-api -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    if [ -z "${SERVICE_IP}" ]; then
        SERVICE_IP=$(kubectl get svc -n "${NAMESPACE}" terrafusion-api -o jsonpath='{.spec.clusterIP}')
    fi
    
    echo "🌐 Service IP: ${SERVICE_IP}"
    
    # Run a health check from within the cluster
    HEALTH_STATUS=$(kubectl run -n "${NAMESPACE}" curl --image=curlimages/curl -i --rm --restart=Never --command -- curl -s -o /dev/null -w "%{http_code}" "http://${SERVICE_IP}/health" 2>/dev/null)
    
    if [ "${HEALTH_STATUS}" == "200" ]; then
        echo "✅ Health check passed"
    else
        echo "⚠️ Warning: Health check returned status ${HEALTH_STATUS}"
    fi
else
    # If using Docker Compose
    CONTAINER_ID=$(docker-compose ps -q web)
    HEALTH_STATUS=$(docker exec "${CONTAINER_ID}" curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null)
    
    if [ "${HEALTH_STATUS}" == "200" ]; then
        echo "✅ Health check passed"
    else
        echo "⚠️ Warning: Health check returned status ${HEALTH_STATUS}"
    fi
fi

echo "----------------------------------------"
echo "🎉 DISASTER RECOVERY PROCEDURE COMPLETED 🎉"
echo "📅 Completed at: $(date)"
echo "📝 Full logs available at: ${LOG_FILE}"
echo "🔄 Recovery performed using backup: ${LATEST_BACKUP}"

# Send notification
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    echo "📣 Sending notification..."
    curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"🚨 TerraFusion disaster recovery for ${ENVIRONMENT} environment completed successfully. Used backup: ${LATEST_BACKUP}\"}" "${SLACK_WEBHOOK_URL}"
fi

echo "📋 Next steps:"
echo "  1. Verify application functionality manually"
echo "  2. Run integration tests"
echo "  3. Check monitoring dashboards"
echo "  4. Update documentation with recovery details"