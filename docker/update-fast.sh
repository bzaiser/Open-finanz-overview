#!/bin/bash

# Exit on any error
set -e

echo "Starting FAST Update Process (No Rebuild)..."

# Move to the project root directory
cd ..

# Save local changes (like DEBUG=True or .env changes) to avoid pull conflicts
echo "Stashing local changes..."
git stash || true

# Pull new changes from git
echo "Pulling from git repository..."
git pull origin master

# Restore local changes
echo "Restoring local changes..."
git stash pop || true

# Move back to the docker folder
cd docker

# Run database migrations (fast if no new ones)
echo "Running database migrations..."
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createcachetable

# Compile translations
echo "Compiling translations..."
docker compose exec web python manage.py compilemessages

# Collect static files
echo "Collecting static files..."
docker compose exec web python manage.py collectstatic --noinput

echo "-----------------------------------"
echo "FAST Update complete! The UI/Code is now live."
