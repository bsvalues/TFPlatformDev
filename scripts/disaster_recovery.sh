#!/bin/bash
# Disaster Recovery script for TerraFusion Platform
# This script provides tools for recovering from various failure scenarios

set -e

# Command line arguments
ACTION=$1
TARGET_ENV=${2:-"prod"}  # Default to production environment

# Functions
function print_usage() {
    echo "TerraFusion Platform Disaster Recovery"
    echo "Usage: $0 <action> [environment]"
    echo
    echo "Actions:"
    echo "  backup             - Create a full backup of the system"
    echo "  restore <file>     - Restore system from backup file"
    echo "  rollback <version> - Rollback to a previous version"
    echo "  status             - Check system status"
    echo "  repair-db          - Attempt to repair database"
    echo "  failover           - Initiate failover to standby"
    echo "  help               - Show this help message"
    echo
    echo "Environment: dev, staging, prod (default: prod)"
}

function create_backup() {
    echo "Creating full system backup for $TARGET_ENV environment..."
    
    # Create backup directory
    BACKUP_DIR="backup_${TARGET_ENV}_$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Database backup
    echo "Backing up database..."
    ./scripts/backup.sh
    
    # Copy latest database backup to disaster recovery backup directory
    cp -v /backups/postgres/$(ls -t /backups/postgres | head -1) $BACKUP_DIR/
    
    # Config backup
    echo "Backing up configuration..."
    if [ -f .env.$TARGET_ENV ]; then
        cp -v .env.$TARGET_ENV $BACKUP_DIR/
    fi
    cp -v docker-compose.yml docker-compose.$TARGET_ENV.yml $BACKUP_DIR/
    
    # Code backup
    echo "Backing up code..."
    git bundle create $BACKUP_DIR/code.bundle HEAD
    
    # Create archive
    echo "Creating archive..."
    tar -czf "${BACKUP_DIR}.tar.gz" $BACKUP_DIR
    rm -rf $BACKUP_DIR
    
    echo "Backup completed: ${BACKUP_DIR}.tar.gz"
}

function restore_from_backup() {
    BACKUP_FILE=$2
    if [ -z "$BACKUP_FILE" ]; then
        echo "Error: Backup file not specified"
        echo "Usage: $0 restore <backup_file> [environment]"
        exit 1
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    echo "Restoring system from backup: $BACKUP_FILE"
    
    # Extract backup
    echo "Extracting backup..."
    tar -xzf $BACKUP_FILE
    BACKUP_DIR=$(basename $BACKUP_FILE .tar.gz)
    
    # Stop services
    echo "Stopping services..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml down
    
    # Restore database
    echo "Restoring database..."
    DB_BACKUP=$(ls -1 $BACKUP_DIR/*.sql.gz | head -1)
    if [ -n "$DB_BACKUP" ]; then
        ./scripts/restore.sh $DB_BACKUP
    else
        echo "No database backup found in archive"
    fi
    
    # Restore config
    echo "Restoring configuration..."
    if [ -f $BACKUP_DIR/.env.$TARGET_ENV ]; then
        cp -v $BACKUP_DIR/.env.$TARGET_ENV .env.$TARGET_ENV
    fi
    
    # Restore code if needed
    read -p "Restore code from backup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Restoring code..."
        git bundle unbundle $BACKUP_DIR/code.bundle
    fi
    
    # Start services
    echo "Starting services..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml up -d
    
    # Cleanup
    rm -rf $BACKUP_DIR
    
    echo "System restored successfully"
}

function rollback_version() {
    VERSION=$2
    if [ -z "$VERSION" ]; then
        echo "Error: Version not specified"
        echo "Usage: $0 rollback <version> [environment]"
        echo "Available versions:"
        git tag | grep -v '^$'
        exit 1
    fi
    
    echo "Rolling back to version $VERSION in $TARGET_ENV environment..."
    
    # Create backup before rollback
    echo "Creating backup before rollback..."
    create_backup
    
    # Checkout version
    echo "Checking out version $VERSION..."
    git checkout $VERSION
    
    # Rebuild and restart
    echo "Rebuilding and restarting services..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml up -d --build
    
    echo "Rollback completed"
}

function check_status() {
    echo "Checking system status for $TARGET_ENV environment..."
    
    # Check containers
    echo "Container status:"
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml ps
    
    # Check database
    echo "Database status:"
    if PGPASSWORD=$PGPASSWORD psql -h ${PGHOST:-localhost} -U ${PGUSER:-postgres} -c '\l' | grep -q ${PGDATABASE:-terrafusion}; then
        echo "Database connection: OK"
    else
        echo "Database connection: FAILED"
    fi
    
    # Check API
    echo "API status:"
    if curl -s http://localhost:5000/health | grep -q "healthy"; then
        echo "API health check: OK"
    else
        echo "API health check: FAILED"
    fi
    
    # Check disk space
    echo "Disk space:"
    df -h | grep -E '(Filesystem|/$)'
    
    echo "Status check completed"
}

function repair_database() {
    echo "Attempting to repair database in $TARGET_ENV environment..."
    
    # Create backup before repair
    echo "Creating backup before repair..."
    ./scripts/backup.sh
    
    # Repair PostgreSQL database
    echo "Repairing PostgreSQL database..."
    if [ "$TARGET_ENV" == "prod" ]; then
        # For production, be extra careful
        read -p "This will restart the production database. Are you sure? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Database repair cancelled"
            exit 1
        fi
    fi
    
    # Restart PostgreSQL container
    echo "Restarting PostgreSQL container..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml restart postgres
    
    # Run database vacuum
    echo "Running database vacuum..."
    PGPASSWORD=$PGPASSWORD psql -h ${PGHOST:-localhost} -U ${PGUSER:-postgres} -d ${PGDATABASE:-terrafusion} -c "VACUUM FULL;"
    
    echo "Database repair completed"
}

function initiate_failover() {
    echo "Initiating failover for $TARGET_ENV environment..."
    
    if [ "$TARGET_ENV" != "prod" ]; then
        echo "Failover only supported in production environment"
        exit 1
    fi
    
    # Confirm failover
    read -p "This will failover to the standby system. Are you sure? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Failover cancelled"
        exit 1
    fi
    
    # In a real system, this would trigger failover to a standby system
    # For this example, we'll simulate by restarting services
    echo "Simulating failover to standby system..."
    
    # Stop primary services
    echo "Stopping primary services..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml down
    
    # Start "standby" services
    echo "Starting standby services..."
    docker-compose -f docker-compose.yml -f docker-compose.$TARGET_ENV.yml up -d
    
    echo "Failover completed"
}

# Main script execution
case $ACTION in
    backup)
        create_backup
        ;;
    restore)
        restore_from_backup $@
        ;;
    rollback)
        rollback_version $@
        ;;
    status)
        check_status
        ;;
    repair-db)
        repair_database
        ;;
    failover)
        initiate_failover
        ;;
    help|*)
        print_usage
        ;;
esac