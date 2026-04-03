#!/bin/bash

# Exit on any error
set -e

echo "Starting FAST Update Process (No Rebuild)..."

# Move to the project root directory
cd ..

# Pull new changes from git
echo "Pulling from git repository..."
git pull origin $(git rev-parse --abbrev-ref HEAD)

# Move back to the docker folder
cd docker

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

# Restart the web service to load new code
echo "Restarting the web server..."
docker compose --env-file ../.env restart web

echo "-----------------------------------"
echo "FAST Update complete! The UI/Code is now live."
