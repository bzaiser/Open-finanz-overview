import os
import io
import glob
import zipfile
import sqlite3
import datetime
from django.conf import settings
from django.utils import timezone

def generate_backup_archive():
    """
    Creates a ZIP archive in memory containing:
    1. A consistent live backup of SQLite database (via sqlite3 backup API)
    2. All uploaded media files (documents, contracts, images)
    Returns a tuple of (BytesIO buffer, filename, stats_dict).
    """
    buffer = io.BytesIO()
    db_path = settings.DATABASES['default']['NAME']
    media_dir = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'data', 'media'))

    db_backed_up = False
    media_count = 0

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. SQLite Live Backup
        if os.path.exists(db_path):
            try:
                src_conn = sqlite3.connect(db_path)
                mem_conn = sqlite3.connect(':memory:')
                src_conn.backup(mem_conn)
                src_conn.close()

                if hasattr(mem_conn, 'serialize'):
                    dump = mem_conn.serialize()
                else:
                    with open(db_path, 'rb') as f:
                        dump = f.read()
                mem_conn.close()

                zip_file.writestr('database/db.sqlite3', dump)
                db_backed_up = True
            except Exception as e:
                # Fallback to direct read
                with open(db_path, 'rb') as f:
                    zip_file.writestr('database/db.sqlite3', f.read())
                db_backed_up = True

        # 2. Media Directory
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, media_dir)
                    zip_file.write(full_p, os.path.join('media', rel_p))
                    media_count += 1

    buffer.seek(0)
    timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"finanzplan_backup_{timestamp_str}.zip"

    stats = {
        'db_backed_up': db_backed_up,
        'media_count': media_count,
        'size_bytes': buffer.getbuffer().nbytes,
        'timestamp': timezone.now()
    }
    return buffer, filename, stats


def save_backup_to_directory(target_directory, max_keep=5):
    """
    Writes a new backup archive to target_directory and rotates old backups.
    Returns (success: bool, filepath: str, message: str)
    """
    if not target_directory:
        return False, None, "No target directory specified."

    target_directory = os.path.normpath(target_directory.strip())
    if not os.path.exists(target_directory):
        try:
            os.makedirs(target_directory, exist_ok=True)
        except Exception as e:
            return False, None, f"Could not create directory {target_directory}: {e}"

    buffer, filename, stats = generate_backup_archive()
    target_path = os.path.join(target_directory, filename)

    try:
        with open(target_path, 'wb') as f:
            f.write(buffer.getvalue())
    except Exception as e:
        return False, None, f"Failed to write backup to {target_path}: {e}"

    # Rotate old backups
    try:
        pattern = os.path.join(target_directory, "finanzplan_backup_*.zip")
        existing_backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if len(existing_backups) > max_keep:
            for old_file in existing_backups[max_keep:]:
                try:
                    os.remove(old_file)
                except Exception:
                    pass
    except Exception:
        pass

    return True, target_path, f"Backup successfully saved ({stats['size_bytes'] / (1024*1024):.2f} MB)."


def is_backup_due(profile):
    """
    Determines if a backup should be created or prompted for user profile.
    """
    if not profile or profile.backup_frequency == 'never':
        return False

    today = timezone.localdate()
    if profile.backup_dismissed_until and profile.backup_dismissed_until >= today:
        return False

    last_run = profile.backup_last_run
    if not last_run:
        return True

    now = timezone.now()
    freq = profile.backup_frequency
    if freq == 'daily':
        return (now - last_run).days >= 1
    elif freq == 'weekly':
        return (now - last_run).days >= 7
    elif freq == 'monthly':
        return (now - last_run).days >= 30

    return False
