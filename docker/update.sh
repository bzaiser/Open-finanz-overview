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
mkdir -p "$ROOT_DIR/data/ollama"
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

# Run database migrations
echo "Running database migrations..."
docker compose --env-file ../.env exec web python3 manage.py makemigrations
docker compose --env-file ../.env exec web python3 manage.py migrate
docker compose --env-file ../.env exec web python3 manage.py createcachetable

# Compile translations
echo "Compiling translations..."
docker compose exec web python3 manage.py compilemessages

# Collect static files
echo "Collecting static files..."
docker compose exec web python3 manage.py collectstatic --noinput

# Ensure the correct Ollama model is downloaded
if grep -q "OLLAMA_MODEL" ../.env; then
    MODEL=$(grep -E '^\s*OLLAMA_MODEL\s*=' ../.env | cut -d '=' -f 2 | tr -d '"' | tr -d "'" | tr -d '\r' | tr -d ' ')
    if [ -n "$MODEL" ]; then
        echo "Ensuring Ollama model '$MODEL' is downloaded (this may take a while on first run)..."
        docker compose --env-file ../.env exec -T ollama ollama pull "$MODEL" || echo "Warning: Could not pull Ollama model. Is the container running?"
    fi
fi

echo "-----------------------------------"
echo "Update complete! Application is running."

