#!/bin/bash

# Exit on any error
set -e

echo "Starting Update Process..."

# Move to the project root directory where git lives
cd ..

# Pull new changes from git
echo "Pulling from git repository..."
git pull origin master

# Move back to the docker folder
cd docker

# Rebuild the docker image (fast since it uses cache)
echo "Building the docker image..."
docker compose build

# Start the container in detached mode (recreates only if image/config changed)
echo "Starting the container..."
docker compose up -d

# Run database migrations
echo "Running database migrations..."
docker compose exec web python manage.py migrate

# Compile translations
echo "Compiling translations..."
docker compose exec web python manage.py compilemessages

echo "-----------------------------------"
echo "Update complete! Application is running."

