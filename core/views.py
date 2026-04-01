from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import translation
from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.save()
            # Create profile
            UserProfile.objects.create(user=user)
            login(request, user)
            # Default language from profile
            translation.activate('de')
            request.session[translation.LANGUAGE_SESSION_KEY] = 'de'
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            # Update session and cookie for immediate language switch
            language = profile.language
            translation.activate(language)
            request.session[translation.LANGUAGE_SESSION_KEY] = language
            response = redirect('profile')
            # Use getattr for safety or default to 'django_language'
            cookie_name = getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language')
            response.set_cookie(cookie_name, language)
            return response
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'core/profile.html', {'form': form})

@login_required
def help_view(request):
    return render(request, 'core/help.html')

def about_view(request):
    return render(request, 'core/about.html')
