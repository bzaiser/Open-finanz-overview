from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.utils import translation
from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile, CustomUser

class AppLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if demo family exists
        context['has_demo_family'] = CustomUser.objects.filter(username='demo_familie').exists()
        return context

@require_POST
def load_demo_family_view(request):
    try:
        call_command('seed_demo_family')
        user = CustomUser.objects.filter(username='demo_familie').first()
        if user:
            messages.success(
                request,
                _('Benutzer erfolgreich importiert! Benutzername: demo_familie | Passwort: DemoUser2026!')
            )
        else:
            messages.error(request, _("Demo-Benutzer konnte nicht erstellt werden."))
    except Exception as e:
        messages.error(request, f"{_('Fehler beim Laden der Demodaten')}: {e}")
    return redirect('login')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            if not CustomUser.objects.filter(is_superuser=True).exists():
                user.is_superuser = True
            user.save()
            # Create profile
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('finance:dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def toggle_night_mode(request):
    profile = request.user.profile
    profile.auto_night_mode = not profile.auto_night_mode
    profile.save()
    return redirect(request.META.get('HTTP_REFERER', 'profile'))

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profile updated successfully!"))
            return redirect('finance:dashboard')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'core/profile.html', {
        'form': form
    })

@login_required
def help_view(request):
    return render(request, 'core/help.html')

def about_view(request):
    return render(request, 'core/about.html')
