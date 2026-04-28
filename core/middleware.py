import logging
from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

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
    Injects the user's custom dashboard gradient into the admin header dynamically.
    This ensures that the admin theme follows the user's profile settings.
    """
    def process_response(self, request, response):
        # Only target admin HTML responses
        if request.path.startswith('/admin/') and 'text/html' in response.get('Content-Type', ''):
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    profile = request.user.profile
                    gs = profile.gradient_start or '#6610f2'
                    ge = profile.gradient_end or '#0d6efd'
                    bg = profile.background_color or '#ffffff'
                    
                    # Surgical CSS to only affect the header background and hide default branding if needed
                    style_tag = f"""
                    <style id="dynamic-admin-theme">
                        :root {{
                            --admin-interface-module-background-color: {gs} !important;
                        }}
                        .admin-interface #header {{
                            background: linear-gradient(135deg, {gs} 0%, {ge} 100%) !important;
                        }}
                        /* Targeted styling only for collapsible summaries */
                        .admin-interface .module.collapse details summary {{
                            background: var(--admin-interface-module-background-color) !important;
                            border-color: var(--admin-interface-module-background-color) !important;
                            color: #ffffff !important;
                        }}
                        #header h1 a, #header #user-tools, #header #user-tools a {{
                            color: #ffffff !important;
                        }}
                        /* Apply start color to breadcrumbs and module headers */
                        .breadcrumbs, .module h2, .module caption {{
                            background: {gs} !important;
                            color: #ffffff !important;
                        }}
                        .breadcrumbs a {{
                            color: #ffffff !important;
                            opacity: 0.9;
                        }}
                        /* Hide the logo on the fly */
                        #header #branding img, 
                        #header #branding svg,
                        .admin-interface #header #branding img,
                        .admin-interface #header #branding svg {{
                            display: none !important;
                        }}
                        /* Ensure the branding text is what we want if JS is disabled */
                        #site-name a {{ color: white !important; }}
                    </style>
                    """
                    
                    # Insert the style tag before the closing head or body tag
                    content = response.content.decode('utf-8')
                    
                    # On-the-fly title replacement if not already handled by site_header
                    content = content.replace('Django Administration', 'Finanzplan Admin')
                    content = content.replace('Django-Administration', 'Finanzplan Admin')
                    
                    if '</head>' in content:
                        content = content.replace('</head>', f'{style_tag}</head>')
                    elif '</body>' in content:
                        content = content.replace('</body>', f'{style_tag}</body>')
                    
                    response.content = content.encode('utf-8')
                    if response.get('Content-Length'):
                        response['Content-Length'] = len(response.content)
                except Exception:
                    pass
        return response
