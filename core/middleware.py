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
                    # Use the EXACT SVG for bi-speedometer2 from Bootstrap Icons
                    dashboard_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-speedometer2" viewBox="0 0 16 16"><path d="M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4M3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707M2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10m9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5m-7-1.414A.5.5 0 0 1 5 9.086V8.5a.5.5 0 0 1 1 0v.586a.5.5 0 0 1-.293.457L4.5 9.914A.5.5 0 0 1 4.293 10l-1.207.371zM8 10a2 2 0 1 1 0-4 2 2 0 0 1 0 4"/><path d="M0 8s1.132-2.503 3.423-4.43c.229-.193.447-.35.654-.473L5.203 5.31A4.49 4.49 0 0 0 4.018 10h1.196L3.89 12.167C1.941 10.899 0 8 0 8m16 0s-1.132-2.503-3.423-4.43a5.53 5.53 0 0 0-.654-.473L10.797 5.31c.706.213 1.343.611 1.848 1.09.444.423.791.859 1.033 1.259h-1.196L13.89 12.167c1.941-1.268 3.89-4.167 3.89-4.167"/></svg>"""
                    dashboard_link = f'<a href="{dashboard_url}" class="dashboard-link-admin">{dashboard_icon} Dashboard</a>'.encode('utf-8')
                    
                    # Target both standard and django-admin-interface user tools containers
                    if b'id="user-tools"' in response.content:
                        response.content = response.content.replace(b'id="user-tools">', b'id="user-tools">' + dashboard_link)
                    
                    if response.get('Content-Length'):
                        response['Content-Length'] = str(len(response.content))
                except Exception as e:
                    logger.error(f"Error in DynamicAdminThemeMiddleware: {e}")
        return response
