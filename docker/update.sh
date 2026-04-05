#!/bin/bash

# Exit on any error
set -e

# Find the script's directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting Update Process..."

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

chmod -R 777 "$ROOT_DIR/data"

# Move back to the docker folder for Docker operations
cd "$SCRIPT_DIR"

# Rebuild the docker image (fast since it uses cache)
echo "Building the docker image..."
docker compose --env-file ../.env build

# Start the container in detached mode (recreates only if image/config changed)
echo "Starting the container..."
docker compose --env-file ../.env up -d

# Ensure the data directory is writeable (fixes readonly database errors)
echo "Fixing permissions for data directory..."
sudo chmod -R 777 ../data

# 4. Install requirements (quietly)
echo "Step 4: Syncing requirements..."
docker compose --env-file ../.env exec web pip install -q --no-cache-dir -r requirements.txt

# 5. Database migrations (self-healing)
echo "Step 5: Database migrations..."
docker compose --env-file ../.env exec web python3 manage.py makemigrations --noinput --verbosity 0
docker compose --env-file ../.env exec web python3 manage.py migrate --verbosity 0
docker compose --env-file ../.env exec web python3 manage.py createcachetable --verbosity 0

# 6. Build frontend & translations
echo "Step 6: Processing assets..."
docker compose --env-file ../.env exec web python3 manage.py compilemessages --verbosity 0
docker compose --env-file ../.env exec web python3 manage.py collectstatic --noinput --verbosity 0



echo "-----------------------------------"
echo "Update complete! Application is running."
