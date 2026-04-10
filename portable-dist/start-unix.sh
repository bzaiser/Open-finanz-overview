#!/bin/bash

echo "=========================================="
echo "  Finanzplan Dashboard - Portable Setup   "
echo "=========================================="
echo

# Check for Podman first, then Docker
if command -v podman &> /dev/null; then
    DOCKER_CMD="podman"
elif command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
else
    echo "============================================================"
    echo " [INFO] Weder Podman noch Docker wurden gefunden."
    echo " Dies ist für den Betrieb des Dashboards notwendig."
    echo "============================================================"
    echo
    
    # Detect OS
    case "$(uname)" in
        "Darwin")
            echo "Da du auf einem Mac arbeitest, kannst du Podman Desktop"
            echo "ganz einfach über Homebrew installieren:"
            echo "  brew install --cask podman-desktop"
            echo
            echo "Alternativ hier herunterladen: https://podman-desktop.io/"
            ;;
        "Linux")
            echo "Bitte installiere Podman oder Docker über deinen Paketmanager,"
            echo "zum Beispiel:"
            echo "  Debian/Ubuntu: sudo apt install podman"
            echo "  Fedora:        sudo dnf install podman"
            echo "  Arch:          sudo pacman -S podman"
            echo
            ;;
        *)
            echo "Bitte installiere Podman Desktop: https://podman-desktop.io/"
            ;;
    esac
    echo "Sobald die Installation abgeschlossen ist und das Programm"
    echo "gestartet wurde, führe dieses Skript erneut aus."
    exit 1
fi

NEW_INSTALL=0
# --- PODMAN MACHINE AUTO-START (macOS only) ---
if [ "$DOCKER_CMD" == "podman" ] && [ "$(uname)" == "Darwin" ]; then
    echo "[+] Prüfe Podman Maschine..."
    if ! %DOCKER_CMD% machine list --format "{{.Name}}" | grep -q "."; then
        echo "[+] Keine Podman Maschine gefunden. Initialisiere..."
        %DOCKER_CMD% machine init --cpus 2 --memory 2048
    fi
    
    if ! %DOCKER_CMD% machine list --format "{{.LastUp}}" | grep -qi "Currently"; then
        echo "[+] Podman Maschine ist gestoppt. Starte Maschine..."
        %DOCKER_CMD% machine start
        echo "[+] Warte auf Maschinenzustand..."
        sleep 5
    fi
fi

if [ ! -f .env ]; then
    NEW_INSTALL=1
    echo "[+] Erster Start erkannt: Starte Setup-Assistent..."
    echo
    
    # 1. PORT
    read -p "Welchen Port soll das Dashboard nutzen? [Standard: 8000]: " WEB_PORT
    WEB_PORT=${WEB_PORT:-8000}
    
    # 2. INSTANCE NAME
    read -p "Wie soll deine Instanz heissen? (z.B. Privat) [Standard: Private]: " APP_INSTANCE_NAME
    APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-Private}
    
    # 3. AI PROVIDER
    echo
    echo "Welchen KI-Assistenten möchtest du nutzen?"
    echo "[1] Keinen (Standard)"
    echo "[2] Ollama (Lokal, setzt installierten Ollama-Server voraus)"
    echo "[3] Groq (Cloud, sehr schnell, erfordert API-Key)"
    read -p "Wähle eine Option [1-3]: " AI_CHOICE
    
    LLM_PROVIDER="none"
    OLLAMA_URL="http://localhost:11434"
    GROQ_KEY=""
    
    case $AI_CHOICE in
        2)
            LLM_PROVIDER="ollama"
            read -p "Ollama URL [Standard: http://localhost:11434]: " OLLAMA_URL
            OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}
            ;;
        3)
            LLM_PROVIDER="groq"
            read -p "Bitte gib deinen Groq API-Key ein: " GROQ_KEY
            ;;
    esac

    # Write .env file
    echo "# Automatisch generiert durch Setup-Assistent" > .env
    echo "WEB_PORT=$WEB_PORT" >> .env
    echo "APP_INSTANCE_NAME=$APP_INSTANCE_NAME" >> .env
    echo "LLM_PROVIDER=$LLM_PROVIDER" >> .env
    echo "OLLAMA_BASE_URL=$OLLAMA_URL" >> .env
    echo "GROQ_API_KEY=$GROQ_KEY" >> .env
    echo "DEBUG=False" >> .env
    echo "ALLOWED_HOSTS=*" >> .env
    echo "RUNNING_IN_DOCKER=1" >> .env
    echo "SECRET_KEY=portable_$(date +%s | sha256sum | base64 | head -c 32)" >> .env
    
    echo
    echo "[+] Setup abgeschlossen! .env wurde erstellt."
    echo
else
    # Load WEB_PORT from .env if it exists
    WEB_PORT=$(grep WEB_PORT .env | cut -d '=' -f2)
    WEB_PORT=${WEB_PORT:-8000}
fi

# Ensure db.sqlite3 is a file
if [ ! -f db.sqlite3 ]; then
    NEW_INSTALL=1
    echo "[+] Initialisiere Datenbank-Datei..."
    touch db.sqlite3
fi

# Start the containers
echo "[+] Nutze $DOCKER_CMD für den Start..."
$DOCKER_CMD compose up -d

if [ $? -ne 0 ]; then
    echo "[FEHLER] Der Start ist fehlgeschlagen!"
    exit 1
fi

# Run migrations and seed data on fresh install
if [ "$NEW_INSTALL" == "1" ]; then
    echo "[+] Erster Start erkannt: Erstelle Datenbank-Tabellen..."
    $DOCKER_CMD exec finanzplan-portable python manage.py migrate --noinput
    echo "[+] Befülle Datenbank mit Demo-Daten (User: demo / demo)..."
    $DOCKER_CMD exec finanzplan-portable python manage.py seed_portable --noinput
fi

echo
echo "URL: http://localhost:${WEB_PORT}"
echo "Login: demo / demo"
echo

# Open browser after a small delay
sleep 5
if command -v open &> /dev/null; then
    open "http://localhost:${WEB_PORT}"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:${WEB_PORT}"
fi

echo "=========================================="
echo "  FERTIG! Das Dashboard läuft.           "
echo "=========================================="
