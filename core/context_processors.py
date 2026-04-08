import os

from django.conf import settings

def app_instance_info(request):
    """
    Injects configuration into all templates.
    """
    return {
        'APP_INSTANCE_NAME': os.getenv('APP_INSTANCE_NAME', ''),
        'debug': settings.DEBUG
    }
