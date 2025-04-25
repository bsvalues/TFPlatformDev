#!/bin/bash
# Database restore script for TerraFusion Platform
# This script restores a PostgreSQL database from a backup file

set -e

# Configuration
PGHOST=${PGHOST:-"localhost"}
PGPORT=${PGPORT:-"5432"}
PGUSER=${PGUSER:-"postgres"}
PGDATABASE=${PGDATABASE:-"terrafusion"}

# Check if a backup file was provided
if [ -z "$1" ]; then
    echo "Error: No backup file specified"
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE=$1

# Check if the backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting database restore for TerraFusion Platform"
echo "Database: $PGDATABASE"
echo "Host: $PGHOST"
echo "Backup file: $BACKUP_FILE"

# Confirm restore operation
read -p "WARNING: This will overwrite the existing database. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore operation cancelled"
    exit 0
fi

# Check if we need to create the database
DB_EXISTS=$(PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -tAc "SELECT 1 FROM pg_database WHERE datname='$PGDATABASE'")

if [ -z "$DB_EXISTS" ]; then
    echo "Database does not exist, creating..."
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -c "CREATE DATABASE $PGDATABASE;"
else
    echo "Database exists, dropping and recreating..."
    
    # Close existing connections
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -c "
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '$PGDATABASE'
        AND pid <> pg_backend_pid();"
    
    # Drop and recreate the database
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -c "DROP DATABASE $PGDATABASE;"
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -c "CREATE DATABASE $PGDATABASE;"
fi

# Perform the restore
echo "Restoring database from backup..."
gunzip -c $BACKUP_FILE | PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo "Restore completed successfully"
    
    # Validate the restored database
    echo "Validating restored database..."
    TABLE_COUNT=$(PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
    echo "Found $TABLE_COUNT tables in the restored database"
    
    # Run any post-restore tasks (like updating sequences, etc.)
    echo "Running post-restore tasks..."
    # Add any necessary post-restore commands here
    
    echo "Restore process completed successfully"
else
    echo "Error: Restore failed"
    exit 1
fi