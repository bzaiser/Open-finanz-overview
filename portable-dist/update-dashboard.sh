#!/bin/bash

echo "=========================================="
echo "  Finanzplan Dashboard - Update Assistent "
echo "=========================================="
echo

# Check for Git
if ! command -v git &> /dev/null; then
    echo "[FEHLER] Git wurde nicht gefunden. Update nicht möglich."
    exit 1
fi

# Pull latest changes
echo "[+] Suche nach Updates auf GitHub..."
cd ..
git pull
if [ $? -ne 0 ]; then
    echo "[FEHLER] Git Pull fehlgeschlagen. Bitte Internetverbindung prüfen."
    cd portable-dist
    exit 1
fi
cd portable-dist

# Rebuild and restart
echo "[+] Baue Container neu und starte..."
if command -v podman &> /dev/null; then
    DOCKER_CMD="podman"
else
    DOCKER_CMD="docker"
fi

$DOCKER_CMD compose up -d --build

if [ $? -ne 0 ]; then
    echo "[FEHLER] Rebuild fehlgeschlagen!"
    exit 1
fi

echo
echo "=========================================="
echo "  UPDATE ERFOLGREICH!                     "
echo "=========================================="
