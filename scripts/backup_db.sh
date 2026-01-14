#!/bin/bash

# Configuration
BACKUP_DIR="./backups"
CONTAINER_NAME="remnabot_db"
DB_USER="remnabot"
DB_NAME="remnabot"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +7 -delete

# Perform backup
echo "Creating backup for $DB_NAME..."
docker exec -t $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

echo "Backup saved to $BACKUP_DIR/db_backup_$DATE.sql.gz"
