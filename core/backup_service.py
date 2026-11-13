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

def is_same_volume_as_app(target_directory):
    """
    Checks if the target backup directory is on the exact same drive / mount volume as the app.
    """
    if not target_directory:
        return True
    try:
        norm_target = os.path.abspath(os.path.expanduser(target_directory))
        norm_app = os.path.abspath(settings.BASE_DIR)

        if os.name == 'nt':
            drive_target, _rest1 = os.path.splitdrive(norm_target)
            drive_app, _rest2 = os.path.splitdrive(norm_app)
            return drive_target.upper() == drive_app.upper()
        else:
            # Check mount points on Linux/Unix
            return os.stat(norm_target).st_dev == os.stat(norm_app).st_dev
    except Exception:
        return False

def test_directory_writable(path):
    """
    Checks if a directory actually exists (or can be created) and has write permissions.
    Returns (is_writable, error_message).
    """
    if not path or not path.strip():
        return False, _("Kein Pfad angegeben.")

    clean_path = path.strip()
    # Reject relative paths that don't start with / or drive letter
    if not os.path.isabs(clean_path):
        return False, _("Bitte einen absoluten Pfad angeben (z. B. D:\\Backups oder /volume2/backup).")

    try:
        os.makedirs(clean_path, exist_ok=True)
        test_file = os.path.join(clean_path, f".perm_test_{uuid.uuid4().hex[:6]}")
        with open(test_file, 'w') as f:
            f.write('write_check')
        os.remove(test_file)
        return True, ""
    except Exception as e:
        return False, str(e)

def get_real_accessible_shares():
    """
    Scans the actual filesystem of the host/server/NAS for genuinely existing,
    writable directories and mounted shares. Does NOT return non-existent dummy paths.
    """
    shares = []
    app_drive = os.path.splitdrive(os.path.abspath(settings.BASE_DIR))[0].upper()

    if os.name == 'nt':
        import string
        for letter in string.ascii_uppercase:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                writable, _err = test_directory_writable(drive_path)
                if writable:
                    is_other = (letter != app_drive.rstrip(':'))
                    target_dir = os.path.join(drive_path, 'Backups', 'Finanzplan')
                    shares.append({
                        'label': f"{letter}: Laufwerk ({_('Getrenntes Volume') if is_other else _('App-Laufwerk')})",
                        'path': target_dir,
                        'is_other_volume': is_other,
                        'is_writable': True
                    })
    else:
        # Scan real mount points on Linux / NAS
        candidate_bases = [
            '/volume1', '/volume2', '/volume3', '/volume4',
            '/volumeUSB1', '/volumeUSB2', '/share',
            '/mnt', '/media', '/backup', '/backups'
        ]
        found_bases = set()
        for base in candidate_bases:
            if os.path.exists(base) and os.path.isdir(base):
                # Check top-level or immediate sub-shares
                try:
                    entries = os.listdir(base)
                    for entry in entries:
                        p = os.path.join(base, entry)
                        if os.path.isdir(p):
                            writable, _err = test_directory_writable(p)
                            if writable:
                                backup_subdir = os.path.join(p, 'finanzplan_backup')
                                shares.append({
                                    'label': f"{base}/{entry} ({_('Verfügbares Share')})",
                                    'path': backup_subdir,
                                    'is_other_volume': True,
                                    'is_writable': True
                                })
                except Exception:
                    pass

                # Also test the base itself
                writable, _err = test_directory_writable(base)
                if writable:
                    shares.append({
                        'label': f"{base} ({_('Mountpoint')})",
                        'path': os.path.join(base, 'finanzplan_backup'),
                        'is_other_volume': True,
                        'is_writable': True
                    })

    # Always provide default internal app directory as fallback option
    default_dir = get_default_backup_dir()
    shares.append({
        'label': _("Standard App-Verzeichnis (data/backups)"),
        'path': default_dir,
        'is_other_volume': False,
        'is_writable': True
    })

    return shares

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
            clean = target_directory.strip()
            if not os.path.isabs(clean):
                raise ValueError(_(f"Der Pfad '{clean}' ist kein absoluter Pfad."))
            norm_target_dir = os.path.abspath(os.path.expanduser(clean))

        writable, err_msg = test_directory_writable(norm_target_dir)
        if not writable:
            raise PermissionError(_(f"Keine Schreibrechte im Ordner '{norm_target_dir}': {err_msg}"))

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
    raw_path = (profile.backup_path if profile and profile.backup_path else '').strip()
    if not raw_path:
        target_path = get_default_backup_dir()
    else:
        if not os.path.isabs(raw_path):
            raise ValueError(_(f"Der konfigurierte Sicherungspfad '{raw_path}' ist ungültig (kein absoluter Pfad)."))
        target_path = os.path.abspath(os.path.expanduser(raw_path))

    writable, err_msg = test_directory_writable(target_path)
    if not writable:
        raise PermissionError(_(f"Keine Schreibrechte im Zielordner '{target_path}': {err_msg}"))

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
