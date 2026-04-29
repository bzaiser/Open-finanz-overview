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
                    # Use a LARGER SVG for bi-layout-text-window-reverse (20x20)
                    dashboard_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-layout-text-window-reverse" style="margin-right: 10px; vertical-align: -0.15em;" viewBox="0 0 16 16"><path d="M13 6.5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h5a.5.5 0 0 0 .5-.5zm0 3a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h5a.5.5 0 0 0 .5-.5zm0 3a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h5a.5.5 0 0 0 .5-.5zM5 14.1l.005-9.147 6.005-.003-.005 9.15-6.005.003zM4 4.5V15a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V4.5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1zm.646-1.646a.5.5 0 0 1 .708 0l1 1a.5.5 0 0 1-.708.708l-1-1a.5.5 0 0 1 0-.708z"/></svg>"""
                    # Use forced font-size and weight with !important to win over admin CSS
                    dashboard_link = f'<a href="{dashboard_url}" style="margin-right: 30px; color: white !important; font-size: 1.1rem !important; font-weight: 600 !important; font-family: -apple-system, BlinkMacSystemFont, \\"Segoe UI\\", Roboto, \\"Helvetica Neue\\", Arial, sans-serif !important; text-decoration: none !important; display: inline-flex; align-items: center; transition: all 0.2s ease;">{dashboard_icon} Dashboard</a>'.encode('utf-8')
                    
                    # Target both standard and django-admin-interface user tools containers
                    if b'id="user-tools"' in response.content:
                        response.content = response.content.replace(b'id="user-tools">', b'id="user-tools">' + dashboard_link)
                    
                    if response.get('Content-Length'):
                        response['Content-Length'] = str(len(response.content))
                except Exception as e:
                    logger.error(f"Error in DynamicAdminThemeMiddleware: {e}")
        return response
