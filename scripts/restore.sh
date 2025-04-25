#!/bin/bash
# Database restore script for TerraFusion Platform
# This script restores a PostgreSQL database from a backup file

set -e

# Check if a backup file is provided
if [ -z "$1" ]; then
    echo "Error: No backup file provided"
    echo "Usage: $0 <backup_file>"
    exit 1
fi

BACKUP_FILE=$1

# Check if the backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Configuration
DB_HOST=${PGHOST:-localhost}
DB_PORT=${PGPORT:-5432}
DB_USER=${PGUSER:-postgres}
DB_NAME=${PGDATABASE:-terrafusion}

# Check if PGPASSWORD is set
if [ -z "$PGPASSWORD" ]; then
    echo "Error: PGPASSWORD environment variable is not set"
    exit 1
fi

echo "Starting restore of $DB_NAME database from $BACKUP_FILE"

# Confirm before proceeding
read -p "This will overwrite the existing database. Are you sure? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 1
fi

# Drop existing database connections
echo "Dropping existing connections to $DB_NAME database"
PGPASSWORD=$PGPASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();" postgres

# Restore the database
echo "Restoring database from backup"
gunzip -c $BACKUP_FILE | PGPASSWORD=$PGPASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo "Restore completed successfully"
else
    echo "Restore failed"
    exit 1
fi

echo "Restore process completed"