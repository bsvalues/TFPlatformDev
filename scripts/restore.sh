#!/bin/bash
set -e

# TerraFusion Platform Database Restore Script
# This script restores PostgreSQL databases from S3 backups
# Usage: ./restore.sh [dev|staging|prod] [backup_file]

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "❌ Missing required arguments"
    echo "Usage: ./restore.sh [dev|staging|prod] [backup_file]"
    echo "Example: ./restore.sh prod terrafusion_backup_20250425123456.tar.gz"
    exit 1
fi

ENVIRONMENT=$1
BACKUP_FILE=$2
TIMESTAMP=$(date +%Y%m%d%H%M%S)
RESTORE_DIR="/tmp/terrafusion_restore_${TIMESTAMP}"
S3_BUCKET="s3://terrafusion-backups"
S3_PREFIX="${ENVIRONMENT}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it to use this script."
    exit 1
fi

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "❌ Invalid environment: $ENVIRONMENT"
  echo "Usage: ./restore.sh [dev|staging|prod] [backup_file]"
  exit 1
fi

echo "🚀 Starting TerraFusion Platform restore for $ENVIRONMENT environment using backup $BACKUP_FILE"

# Load environment variables from configuration file
if [ -f ".env.${ENVIRONMENT}" ]; then
    echo "📋 Loading environment variables from .env.${ENVIRONMENT}"
    source ".env.${ENVIRONMENT}"
else
    echo "⚠️ Warning: Environment file .env.${ENVIRONMENT} not found. Using existing environment variables."
fi

# Create restore directory
mkdir -p "${RESTORE_DIR}"
echo "📁 Created restore directory at ${RESTORE_DIR}"

# Download backup from S3
echo "☁️ Downloading backup from S3..."
aws s3 cp "${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" "${RESTORE_DIR}/${BACKUP_FILE}"
echo "✅ Download from S3 completed"

# Extract backup
echo "📦 Extracting backup files..."
tar -xzf "${RESTORE_DIR}/${BACKUP_FILE}" -C "${RESTORE_DIR}"
echo "✅ Extraction completed"

# Find the dump file in the extracted directory
DUMP_FILE=$(find "${RESTORE_DIR}" -name "*.dump" | head -1)
if [ -z "${DUMP_FILE}" ]; then
    echo "❌ No PostgreSQL dump file found in the backup"
    exit 1
fi
echo "🔍 Found PostgreSQL dump file: ${DUMP_FILE}"

# Confirm before proceeding
echo "⚠️ WARNING: This will replace the current database with the backup data."
echo "⚠️ All current data in ${PGDATABASE} on ${PGHOST} will be lost."
echo "⚠️ Environment: ${ENVIRONMENT}"
echo -n "Are you sure you want to proceed? [y/N] "
read -r confirmation
if [[ ! "${confirmation}" =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled"
    rm -rf "${RESTORE_DIR}"
    exit 1
fi

# Drop and recreate the database
echo "🗑️ Dropping existing database..."
PGPASSWORD="${PGPASSWORD}" dropdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${PGDATABASE}" --if-exists
echo "🔄 Creating new database..."
PGPASSWORD="${PGPASSWORD}" createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${PGDATABASE}"

# Restore PostgreSQL database
echo "💾 Restoring PostgreSQL database from ${DUMP_FILE}..."
pg_restore -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" -v "${DUMP_FILE}"
echo "✅ PostgreSQL restore completed"

# Clean up local files
echo "🧹 Cleaning up local restore files..."
rm -rf "${RESTORE_DIR}"
echo "✅ Local cleanup completed"

echo "🎉 TerraFusion Platform restore process completed successfully for $ENVIRONMENT environment!"
echo "📊 Restore Stats:"
echo "  Environment: $ENVIRONMENT"
echo "  Backup File: $BACKUP_FILE"
echo "  Timestamp: $TIMESTAMP"
echo "  Database: ${PGDATABASE} on ${PGHOST}"