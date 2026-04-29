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
                    # Use an SVG icon for the dashboard (speedometer/chart-like)
                    dashboard_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" style="margin-right: 5px; vertical-align: text-bottom;" viewBox="0 0 16 16"><path d="M8 2a.5.5 0 0 1 .5.5V4a.5.5 0 0 1-1 0V2.5A.5.5 0 0 1 8 2zM3.732 3.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 8a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 8zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm-7-5.414A.5.5 0 0 1 5 2.086V1.5a.5.5 0 0 1 1 0v.586a.5.5 0 0 1-.293.457l-1.207.371zM8 15a6.974 6.974 0 0 1-4.95-2.05 5 5 0 0 1 9.9 0A6.974 6.974 0 0 1 8 15zM4.646 5.354a.5.5 0 0 1 0-.708l1.207-1.207a.5.5 0 0 1 .708.708L5.354 5.354a.5.5 0 0 1-.708 0z"/></svg>"""
                    dashboard_link = f'<a href="{dashboard_url}" style="margin-right: 20px; color: white !important; font-weight: bold; text-decoration: none; display: inline-flex; align-items: center;">{dashboard_icon} Dashboard</a>'.encode('utf-8')
                    
                    # Target both standard and django-admin-interface user tools containers
                    if b'id="user-tools"' in response.content:
                        response.content = response.content.replace(b'id="user-tools">', b'id="user-tools">' + dashboard_link)
                    
                    if response.get('Content-Length'):
                        response['Content-Length'] = str(len(response.content))
                except Exception as e:
                    logger.error(f"Error in DynamicAdminThemeMiddleware: {e}")
        return response
