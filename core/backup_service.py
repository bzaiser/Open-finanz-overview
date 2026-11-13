import os
import io
import glob
import uuid
import zipfile
import sqlite3
import threading
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

# Thread-safe in-memory job storage
BACKUP_JOBS = {}
_jobs_lock = threading.Lock()

def get_default_backup_dir():
    """Returns the default backups directory inside data/backups."""
    path = os.path.join(settings.BASE_DIR, 'data', 'backups')
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)

def get_suggested_backup_paths():
    """
    Returns list of suggested valid backup directories depending on OS / environment.
    """
    suggestions = [
        {
            'label': _("Standard App-Verzeichnis (Empfohlen)"),
            'path': get_default_backup_dir(),
            'desc': _("Liegt direkt im Datenordner der Anwendung (Server/Desktop).")
        }
    ]

    # Windows Desktop candidates
    if os.name == 'nt':
        user_profile = os.environ.get('USERPROFILE', '')
        if user_profile:
            docs_backup = os.path.join(user_profile, 'Documents', 'Finanzplan_Backups')
            suggestions.append({
                'label': _("Windows Eigene Dokumente"),
                'path': docs_backup,
                'desc': _("Lokaler Dokumentenordner auf diesem PC.")
            })
        for drive in ['D:\\', 'E:\\', 'F:\\']:
            if os.path.exists(drive):
                suggestions.append({
                    'label': f"{drive} { _('Laufwerk') }",
                    'path': os.path.join(drive, 'Backups', 'Finanzplan'),
                    'desc': _("Externes / Zweites Laufwerk auf dem Host.")
                })
    else:
        # Linux / NAS candidates (Synology / QNAP / Docker / Generic Linux)
        nas_candidates = [
            ('/volume1/backups/finanzplan', 'Synology NAS (Volume 1)'),
            ('/share/Backups/finanzplan', 'QNAP NAS (Share)'),
            ('/var/backups/finanzplan', 'Linux Server (/var/backups)'),
            ('/backup', 'Docker Backup Mount (/backup)'),
        ]
        for c_path, c_label in nas_candidates:
            suggestions.append({
                'label': c_label,
                'path': c_path,
                'desc': _("Verzeichnis auf dem Server/NAS.")
            })

    return suggestions

def get_job_status(job_id):
    with _jobs_lock:
        return BACKUP_JOBS.get(job_id, None)

def update_job_status(job_id, **kwargs):
    with _jobs_lock:
        if job_id in BACKUP_JOBS:
            BACKUP_JOBS[job_id].update(kwargs)

def _backup_worker_task(job_id, profile_id, target_directory, max_keep):
    try:
        from core.models import UserProfile
        profile = UserProfile.objects.filter(id=profile_id).first()

        update_job_status(
            job_id,
            status='running',
            progress=5,
            step_label=_("Berechne Dateien für Datensicherung...")
        )

        db_path = settings.DATABASES['default']['NAME']
        media_dir = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'data', 'media'))

        # Prepare target folder
        if not target_directory or not target_directory.strip():
            norm_target_dir = get_default_backup_dir()
        else:
            norm_target_dir = os.path.abspath(os.path.expanduser(target_directory.strip()))
        os.makedirs(norm_target_dir, exist_ok=True)

        timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        target_filename = f"finanzplan_backup_{timestamp_str}.zip"
        target_filepath = os.path.join(norm_target_dir, target_filename)

        # Collect media files
        media_files = []
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, media_dir)
                    media_files.append((full_p, os.path.join('media', rel_p)))

        update_job_status(
            job_id,
            progress=15,
            step_label=_("Erstelle konsistentes Datenbank-Abbild (SQLite)...")
        )

        with zipfile.ZipFile(target_filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
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
                except Exception:
                    with open(db_path, 'rb') as f:
                        zip_file.writestr('database/db.sqlite3', f.read())

            update_job_status(
                job_id,
                progress=25,
                step_label=_("Datenbank gesichert. Komprimiere Dokumente & Belege...")
            )

            # 2. Add media files with progress reporting
            total_media = len(media_files)
            for idx, (full_p, zip_p) in enumerate(media_files, start=1):
                try:
                    zip_file.write(full_p, zip_p)
                except Exception:
                    pass

                current_progress = 25 + int((idx / max(total_media, 1)) * 65)
                if idx % 5 == 0 or idx == total_media:
                    update_job_status(
                        job_id,
                        progress=min(current_progress, 90),
                        step_label=_(f"Komprimiere Dokumente ({idx} / {total_media})...")
                    )

        # 3. Finalize & Rotate
        update_job_status(
            job_id,
            progress=95,
            step_label=_("Bereinige ältere Sicherungen...")
        )

        # Retention rotation
        try:
            pattern = os.path.join(norm_target_dir, "finanzplan_backup_*.zip")
            existing_backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
            if len(existing_backups) > max_keep:
                for old_file in existing_backups[max_keep:]:
                    try:
                        os.remove(old_file)
                    except Exception:
                        pass
        except Exception:
            pass

        file_size_mb = os.path.getsize(target_filepath) / (1024 * 1024)

        if profile:
            profile.backup_last_run = timezone.now()
            profile.backup_dismissed_until = None
            profile.save(update_fields=['backup_last_run', 'backup_dismissed_until'])

        update_job_status(
            job_id,
            status='completed',
            progress=100,
            step_label=_(f"Sicherung erfolgreich erstellt ({file_size_mb:.2f} MB)!"),
            target_file=target_filepath,
            filename=target_filename,
            target_directory=norm_target_dir,
            file_size_mb=file_size_mb
        )

    except Exception as e:
        update_job_status(
            job_id,
            status='failed',
            error=str(e),
            step_label=_(f"Fehler bei Sicherung: {e}")
        )

def start_background_backup(profile):
    """
    Spawns a background thread to generate and save backup into profile.backup_path or default folder.
    Returns (job_id, target_directory).
    """
    target_path = (profile.backup_path if profile and profile.backup_path else '').strip()
    if not target_path:
        target_path = get_default_backup_dir()
    else:
        target_path = os.path.abspath(os.path.expanduser(target_path))

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        BACKUP_JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': 0,
            'step_label': _("Initialisiere Datensicherung..."),
            'target_file': None,
            'target_directory': target_path,
            'error': None,
            'created_at': timezone.now()
        }

    max_keep = profile.backup_max_keep if profile else 5
    profile_id = profile.id if profile else None

    thread = threading.Thread(
        target=_backup_worker_task,
        args=(job_id, profile_id, target_path, max_keep),
        daemon=True
    )
    thread.start()
    return job_id, target_path

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
