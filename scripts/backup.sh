#!/bin/bash
set -e

# TerraFusion Platform Database Backup Script
# This script performs backups of PostgreSQL databases to S3
# Usage: ./backup.sh [dev|staging|prod]

# Default to prod if no environment specified
ENVIRONMENT=${1:-prod}
TIMESTAMP=$(date +%Y%m%d%H%M%S)
BACKUP_DIR="/tmp/terrafusion_backup_${TIMESTAMP}"
S3_BUCKET="s3://terrafusion-backups"
S3_PREFIX="${ENVIRONMENT}"
RETENTION_DAYS=30  # How many days to keep backups

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it to use this script."
    exit 1
fi

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "❌ Invalid environment: $ENVIRONMENT"
  echo "Usage: ./backup.sh [dev|staging|prod]"
  exit 1
fi

echo "🚀 Starting TerraFusion Platform backup for $ENVIRONMENT environment"

# Load environment variables from configuration file
if [ -f ".env.${ENVIRONMENT}" ]; then
    echo "📋 Loading environment variables from .env.${ENVIRONMENT}"
    source ".env.${ENVIRONMENT}"
else
    echo "⚠️ Warning: Environment file .env.${ENVIRONMENT} not found. Using existing environment variables."
fi

# Create backup directory
mkdir -p "${BACKUP_DIR}"
echo "📁 Created backup directory at ${BACKUP_DIR}"

# Backup PostgreSQL database
echo "💾 Backing up PostgreSQL database..."
pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -F c -f "${BACKUP_DIR}/postgres_${TIMESTAMP}.dump"
echo "✅ PostgreSQL backup completed"

# Compress the backup directory
echo "🗜️ Compressing backup files..."
tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "${BACKUP_DIR}")" "$(basename "${BACKUP_DIR}")"
echo "✅ Compression completed"

# Upload to S3
echo "☁️ Uploading backup to S3..."
aws s3 cp "${BACKUP_DIR}.tar.gz" "${S3_BUCKET}/${S3_PREFIX}/terrafusion_backup_${TIMESTAMP}.tar.gz"
echo "✅ Upload to S3 completed"

# Clean up local files
echo "🧹 Cleaning up local backup files..."
rm -rf "${BACKUP_DIR}" "${BACKUP_DIR}.tar.gz"
echo "✅ Local cleanup completed"

# Remove old backups from S3 (older than RETENTION_DAYS)
echo "🗑️ Removing backups older than ${RETENTION_DAYS} days from S3..."
aws s3 ls "${S3_BUCKET}/${S3_PREFIX}/" | grep "terrafusion_backup_" | awk '{print $4}' | while read -r backup_file; do
    backup_date=$(echo "$backup_file" | grep -oP 'terrafusion_backup_\K\d{14}' | cut -c1-8)
    current_date=$(date +%Y%m%d)
    
    # Calculate days difference using date command
    days_diff=$(( ( $(date -d "$current_date" +%s) - $(date -d "$backup_date" +%s) ) / 86400 ))
    
    if [ "$days_diff" -gt "$RETENTION_DAYS" ]; then
        echo "🗑️ Removing old backup: $backup_file (${days_diff} days old)"
        aws s3 rm "${S3_BUCKET}/${S3_PREFIX}/$backup_file"
    fi
done
echo "✅ Cleanup of old backups completed"

echo "🎉 TerraFusion Platform backup process completed successfully for $ENVIRONMENT environment!"
echo "📊 Backup Stats:"
echo "  Environment: $ENVIRONMENT"
echo "  Timestamp: $TIMESTAMP"
echo "  S3 Location: ${S3_BUCKET}/${S3_PREFIX}/terrafusion_backup_${TIMESTAMP}.tar.gz"
echo "  Retention Policy: ${RETENTION_DAYS} days"