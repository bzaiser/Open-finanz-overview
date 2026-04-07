import os

def app_instance_info(request):
    """
    Injects the APP_INSTANCE_NAME from environment variables into all templates.
    Used to distinguish between 'Private' and 'Open' server instances in the UI.
    """
    return {
        'APP_INSTANCE_NAME': os.getenv('APP_INSTANCE_NAME', '')
    }
