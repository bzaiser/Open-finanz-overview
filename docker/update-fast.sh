#!/bin/bash

# Exit on any error
set -e

# Find the script's directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting FAST Update Process (No Rebuild)..."

# Move to the project root directory
cd "$ROOT_DIR"

# Pull new changes from git
echo "Pulling from git repository..."
git pull origin $(git rev-parse --abbrev-ref HEAD)

# Move back to the docker folder for Docker operations
cd "$SCRIPT_DIR"

# Run database migrations (fast if no new ones)
echo "Running database migrations..."
docker compose --env-file ../.env exec web python manage.py migrate
docker compose --env-file ../.env exec web python manage.py createcachetable

# Compile translations
echo "Compiling translations..."
docker compose --env-file ../.env exec web python manage.py compilemessages

# Collect static files
echo "Collecting static files..."
docker compose --env-file ../.env exec web python manage.py collectstatic --noinput

# Restart/Recreate the services to load new code/config
echo "Updating containers..."
docker compose --env-file ../.env up -d

echo "-----------------------------------"
echo "FAST Update complete! The UI/Code is now live."
