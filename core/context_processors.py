import functools
import os
import subprocess

from django.conf import settings

@functools.lru_cache(maxsize=1)
def get_git_version_info():
    version = os.getenv('APP_VERSION')
    date = os.getenv('APP_VERSION_DATE')
    if version and date:
        return {'version': version, 'date': date}

    repo_dir = settings.BASE_DIR
    try:
        if not version:
            version = subprocess.check_output(
                ['git', 'describe', '--tags', '--always'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
    except Exception:
        version = 'unknown'

    try:
        if not date:
            date = subprocess.check_output(
                ['git', 'log', '-1', '--format=%cs'],
                cwd=repo_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
    except Exception:
        date = ''

    return {
        'version': version if version else 'unknown',
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

