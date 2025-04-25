#!/bin/bash
# Database backup script for TerraFusion Platform
# This script performs daily backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backups/postgres"
BACKUP_RETENTION_DAYS=7
DB_HOST=${PGHOST:-localhost}
DB_PORT=${PGPORT:-5432}
DB_USER=${PGUSER:-postgres}
DB_NAME=${PGDATABASE:-terrafusion}
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Check if PGPASSWORD is set
if [ -z "$PGPASSWORD" ]; then
    echo "Error: PGPASSWORD environment variable is not set"
    exit 1
fi

echo "Starting backup of $DB_NAME database"

# Perform database backup
PGPASSWORD=$PGPASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
else
    echo "Backup failed"
    exit 1
fi

# Delete old backups
echo "Cleaning up old backups (older than $BACKUP_RETENTION_DAYS days)"
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION_DAYS -delete

echo "Backup process completed"