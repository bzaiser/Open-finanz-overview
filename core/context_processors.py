import functools
import os
import subprocess

from django.conf import settings

DEFAULT_APP_VERSION = 'v0.9-beta'

@functools.lru_cache(maxsize=1)
def get_git_version_info():
    version = os.getenv('APP_VERSION')
    date = os.getenv('APP_VERSION_DATE')
    if version and date:
        return {'version': version, 'date': date}

    repo_dir = settings.BASE_DIR

    # Check for version and date files written during build/deployment
    version_file = repo_dir / 'VERSION'
    if not version and version_file.exists():
        try:
            version = version_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass

    date_file = repo_dir / 'VERSION_DATE'
    if not date and date_file.exists():
        try:
            date = date_file.read_text(encoding='utf-8').strip()
        except Exception:
            pass

    if not version:
        try:
            version = subprocess.check_output(
                ['git', 'describe', '--tags', '--always'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except Exception:
            version = DEFAULT_APP_VERSION

    if not date:
        try:
            date = subprocess.check_output(
                ['git', 'log', '-1', '--format=%cs'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except Exception:
            date = ''

    return {
        'version': version or DEFAULT_APP_VERSION,
        'date': date or ''
    }

def app_instance_info(request):
    """
    Injects configuration into all templates.
    """
    version_info = get_git_version_info()
    return {
        'APP_INSTANCE_NAME': os.getenv('APP_INSTANCE_NAME', ''),
        'APP_VERSION': version_info['version'],
        'APP_VERSION_DATE': version_info['date'],
        'debug': settings.DEBUG
    }

