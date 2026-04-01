from django.utils import translation
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class UserLanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set the active language based on the user's profile preference.
    Runs after LocaleMiddleware to override it.
    """
    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                language = profile.language
                if language:
                    translation.activate(language)
                    request.LANGUAGE_CODE = translation.get_language()
                    # Ensure session and cookies are synced
                    if request.session.get(translation.LANGUAGE_SESSION_KEY) != language:
                        request.session[translation.LANGUAGE_SESSION_KEY] = language
            except Exception:
                pass
