import logging
from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse

logger = logging.getLogger(__name__)

class UserLanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set the active language based on the user's profile preference.
    Runs after AuthenticationMiddleware so request.user is set.
    """
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                language = profile.language
                if language:
                    translation.activate(language)
                    request.LANGUAGE_CODE = translation.get_language()
                    # logger.info(f"Activated language '{language}' for user '{request.user.username}'")
                    
                    # Ensure session and cookies are synced
                    if request.session.get(translation.LANGUAGE_SESSION_KEY) != language:
                        request.session[translation.LANGUAGE_SESSION_KEY] = language
            except Exception as e:
                # logger.error(f"Error in UserLanguageMiddleware: {e}")
                pass

class DynamicAdminThemeMiddleware(MiddlewareMixin):
    """
    Injects a link to the dynamic theme CSS into the admin header.
    This ensures that the admin theme follows the user's profile settings
    without bloating every HTML response with inline styles.
    """
    def process_response(self, request, response):
        # Only target admin HTML responses
        if request.path.startswith('/admin/') and 'text/html' in response.get('Content-Type', ''):
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    # 1. Inject the link to our dynamic CSS view
                    theme_url = reverse('finance:dynamic_theme_css')
                    link_tag = f'<link rel="stylesheet" href="{theme_url}" id="dynamic-admin-theme">'.encode('utf-8')
                    
                    if b'</head>' in response.content:
                        response.content = response.content.replace(b'</head>', link_tag + b'</head>')
                    elif b'</body>' in response.content:
                        response.content = response.content.replace(b'</body>', link_tag + b'</body>')
                    
                    # 2. Inject the Dashboard link into the user tools area
                    dashboard_url = reverse('finance:dashboard')
                    # Use standard Bootstrap Icon class (CSS imported via dynamic_theme_css)
                    dashboard_icon = '<i class="bi bi-speedometer2" style="margin-right: 6px; font-size: 16px; vertical-align: middle;"></i>'
                    dashboard_link = f'<a href="{dashboard_url}" class="dashboard-link-admin">{dashboard_icon} Dashboard</a>'.encode('utf-8')
                    
                    # Target both standard and django-admin-interface user tools containers
                    if b'id="user-tools"' in response.content:
                        response.content = response.content.replace(b'id="user-tools">', b'id="user-tools">' + dashboard_link)
                    
                    if response.get('Content-Length'):
                        response['Content-Length'] = str(len(response.content))
                except Exception as e:
                    logger.error(f"Error in DynamicAdminThemeMiddleware: {e}")
        return response
