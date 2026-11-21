#!/bin/bash
# Einheitliches Baukasten FAST-Update (persistente Kits in /opt/ds-pkg, kein Rebuild)
# Optionen:
#   --no-kits     Ueberspringt Kit-Sync (nur App-Code + Migrationen + Restart)
#   --deps        Erzwingt Installation externer PyPI-Pakete aus requirements.txt
#   --force-kits  Installiert alle aktiven Baukasten-Kits neu nach /opt/ds-pkg
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

NO_KITS=0
FORCE_DEPS=0
FORCE_KITS=0
for arg in "$@"; do
    case "$arg" in
        --no-kits) NO_KITS=1 ;;
        --deps) FORCE_DEPS=1 ;;
        --force-kits) FORCE_KITS=1 ;;
    esac
done

ENV_ARG=""
[ -f ".env" ] && ENV_ARG="--env-file .env"

echo "⚡ Starte FAST Update..."

# 1. Git Pull (clean untracked .mo files that could block merge)
OLD_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
if [ -d "locale" ]; then
    find locale -name "*.mo" -type f -delete 2>/dev/null || true
fi
if [ -d ".git" ] && git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "⏬ Git pull..."
    git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
fi

if [ -d ".git" ]; then
    git describe --tags --always > VERSION 2>/dev/null || git rev-parse --short HEAD > VERSION 2>/dev/null || true
    git log -1 --format="%cs" > VERSION_DATE 2>/dev/null || true
fi

# 2. Permissions & persistent directories
echo "🔐 Berechtigungen & Datenverzeichnis..."
chmod -R a+rX . 2>/dev/null || true
[ -f "manage.py" ] && chmod +x manage.py 2>/dev/null || true
mkdir -p "$ROOT_DIR/data" "$ROOT_DIR/data/backups"
chmod -R 777 "$ROOT_DIR/data" 2>/dev/null || true

# 3. Ensure container is running & persistent /opt/ds-pkg volume is writable
docker compose $ENV_ARG up -d
docker compose $ENV_ARG exec -u 0 web sh -c "mkdir -p /opt/ds-pkg && chmod 777 /opt/ds-pkg" 2>/dev/null || true

# 4. External PyPI deps ONLY when requirements.txt changed (exclude Baukasten kit URLs so kits never duplicate into site-packages)
if [ "$FORCE_DEPS" = "1" ] || { [ -n "$OLD_HEAD" ] && git diff --name-only "$OLD_HEAD" HEAD 2>/dev/null | grep -q "^requirements\.txt$"; }; then
    echo "📦 Aktualisiere externe Python-Pakete (ohne Baukasten-Kits)..."
    docker compose $ENV_ARG exec -u 0 web sh -c 'grep -Ev "(django-design-studio|-django-kit)" requirements.txt > /tmp/req_ext.txt || true; [ -s /tmp/req_ext.txt ] && pip install -q --no-cache-dir --root-user-action=ignore -r /tmp/req_ext.txt || true'
fi

# 5. Sync Baukasten kits persistently into /opt/ds-pkg (only changed commits!)
if [ "$NO_KITS" = "0" ]; then
    echo "🧩 Synchronisiere Baukasten-Kits nach /opt/ds-pkg..."
    SYNC_FLAG=""
    [ "$FORCE_KITS" = "1" ] && SYNC_FLAG="--force"
    if docker compose $ENV_ARG exec web python manage.py help ops_sync_kits >/dev/null 2>&1; then
        docker compose $ENV_ARG exec web python manage.py ops_sync_kits $SYNC_FLAG
    else
        echo "  → Initial-Bootstrap der Baukasten-Kits nach /opt/ds-pkg..."
        docker compose $ENV_ARG exec web sh -c 'grep -E "(django-design-studio|-django-kit)" requirements.txt > /tmp/req_kits.txt || true; [ -s /tmp/req_kits.txt ] && pip install --upgrade --force-reinstall --no-deps --no-cache-dir --target /opt/ds-pkg -r /tmp/req_kits.txt || true'
        if docker compose $ENV_ARG exec web python manage.py help ops_sync_kits >/dev/null 2>&1; then
            docker compose $ENV_ARG exec web python manage.py ops_sync_kits --force
        fi
    fi
fi

# 6. Database migrations (auto-detect multi-tenant migrate_all vs standard migrate)
echo "⚙️ Datenbank-Migrationen..."
if [ -f "core/management/commands/migrate_all.py" ]; then
    docker compose $ENV_ARG exec web python manage.py migrate_all
else
    docker compose $ENV_ARG exec web python manage.py migrate --noinput
fi
if grep -q "DatabaseCache" config/settings.py 2>/dev/null; then
    docker compose $ENV_ARG exec web python manage.py createcachetable 2>/dev/null || true
fi

# 7. Translations (if locale/ exists) & static files
if [ -d "locale" ]; then
    echo "🌍 Kompiliere Uebersetzungen..."
    docker compose $ENV_ARG exec web python manage.py compilemessages 2>/dev/null || true
fi
echo "🎨 Sammle statische Dateien..."
docker compose $ENV_ARG exec web python manage.py collectstatic --noinput

# 8. Restart web container
echo "🔄 Starte Container neu..."
docker compose $ENV_ARG restart web

echo "-----------------------------------"
echo "✅ FAST Update abgeschlossen!"
