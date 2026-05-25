#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python3 -m alembic -c fastapi_app/alembic.ini upgrade head

# Execute the original command
echo "Starting application..."
exec "$@"
