#!/bin/bash
# Database backup script for TerraFusion Platform
# This script creates automated backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR=${BACKUP_DIR:-"/backups/postgres"}
PGHOST=${PGHOST:-"localhost"}
PGPORT=${PGPORT:-"5432"}
PGUSER=${PGUSER:-"postgres"}
PGDATABASE=${PGDATABASE:-"terrafusion"}
RETENTION_DAYS=${RETENTION_DAYS:-"7"}  # Number of days to keep backups

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Generate timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/$PGDATABASE-$TIMESTAMP.sql.gz"

echo "Starting database backup for TerraFusion Platform"
echo "Database: $PGDATABASE"
echo "Host: $PGHOST"
echo "Backup file: $BACKUP_FILE"

# Perform the backup
echo "Creating database backup..."
pg_dump -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE | gzip > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Set file permissions
    chmod 640 $BACKUP_FILE
    
    # Calculate backup size
    BACKUP_SIZE=$(du -h $BACKUP_FILE | awk '{print $1}')
    echo "Backup size: $BACKUP_SIZE"
    
    # Remove backups older than retention period
    echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    find $BACKUP_DIR -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    
    # List remaining backups
    echo "Current backups:"
    ls -lh $BACKUP_DIR
else
    echo "Error: Backup failed"
    exit 1
fi

# Optional: Copy backup to remote storage
if [ -n "$REMOTE_BACKUP_ENABLED" ] && [ "$REMOTE_BACKUP_ENABLED" = "true" ]; then
    echo "Copying backup to remote storage..."
    
    if [ -n "$S3_BUCKET" ]; then
        echo "Copying to S3 bucket: $S3_BUCKET"
        aws s3 cp $BACKUP_FILE s3://$S3_BUCKET/database-backups/
    fi
    
    if [ -n "$REMOTE_HOST" ]; then
        echo "Copying to remote host: $REMOTE_HOST"
        scp $BACKUP_FILE $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
    fi
fi

echo "Backup process completed"