#!/bin/bash

# Exit on any error
set -e

# Find the script's directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting FAST Update Process (No Rebuild)..."

# Move to the project root directory for all operations
cd "$ROOT_DIR"

# Pull new changes from git
echo "Pulling from git repository..."
git pull origin $(git rev-parse --abbrev-ref HEAD)

# Fix permissions for the Docker user
echo "Ensuring project-wide permissions..."
chmod -R a+rwX .
chmod +x manage.py

# Ensure data and ollama directories exist
echo "Preparing data directories..."
mkdir -p "$ROOT_DIR/data/ollama"
chmod -R 777 "$ROOT_DIR/data"

# Install potential new requirements (FAST update)
echo "Syncing requirements..."
docker compose --env-file .env exec web pip install -q --no-cache-dir -r requirements.txt

# Run database migrations
echo "Ensuring database migrations are up to date..."
docker compose --env-file .env exec web python3 manage.py migrate --verbosity 0
docker compose --env-file .env exec web python3 manage.py createcachetable --verbosity 0

# Compile translations
echo "Compiling translations..."
docker compose --env-file .env exec web python3 manage.py compilemessages --verbosity 0

# Collect static files
echo "Collecting static files..."
docker compose --env-file .env exec web python3 manage.py collectstatic --noinput --verbosity 0

# Update/Restart the services
echo "Updating containers..."
docker compose --env-file .env up -d
docker compose --env-file .env restart web

echo "-----------------------------------"
echo "FAST Update complete! The UI/Code is now live."
