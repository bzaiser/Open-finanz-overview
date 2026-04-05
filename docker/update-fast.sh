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

# Fix permissions for the Docker user (prevents 'Permission denied' on manage.py and locale files)
echo "Ensuring project-wide permissions..."
chmod -R a+rwX .
chmod +x manage.py

# Ensure data and ollama directories exist to prevent mount failures
echo "Preparing data directories..."
mkdir -p "$ROOT_DIR/data/ollama"
chmod -R 777 "$ROOT_DIR/data"

# Move back to the docker folder for Docker operations
cd "$SCRIPT_DIR"

# Run database migrations (fast if no new ones)
echo "Running database migrations..."
docker compose --env-file ../.env exec web python3 manage.py makemigrations
docker compose --env-file ../.env exec web python3 manage.py migrate
docker compose --env-file ../.env exec web python3 manage.py createcachetable

# Compile translations
echo "Compiling translations..."
docker compose --env-file ../.env exec web python3 manage.py compilemessages

# Collect static files
echo "Collecting static files..."
docker compose --env-file ../.env exec web python3 manage.py collectstatic --noinput

# Restart/Recreate the services to load new code/config
echo "Updating containers..."
docker compose --env-file ../.env up -d
docker compose --env-file ../.env restart web


echo "-----------------------------------"
echo "FAST Update complete! The UI/Code is now live."
