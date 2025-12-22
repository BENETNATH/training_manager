#!/bin/sh
set -e

# Wait for database to be ready if using MySQL/MariaDB
if [ "$DB_TYPE" = "mysql" ] || [ "$DB_TYPE" = "mariadb" ]; then
    echo "Waiting for database to be ready..."
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 1
    done
    echo "Database is ready!"
fi

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Execute the main command
exec "$@"
