from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.views.decorators.http import require_POST
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext as _
import datetime
from django.utils import translation, timezone
from .forms import CustomUserCreationForm, UserProfileForm, AppAuthenticationForm
from .models import UserProfile, CustomUser, DesignHarmony

class AppLoginView(LoginView):
    template_name = 'core/login.html'
    form_class = AppAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me', True)
        if remember_me:
            # Keep session active for standard duration (14 days)
            self.request.session.set_expiry(getattr(settings, 'SESSION_COOKIE_AGE', 1209600))
        else:
            # Session expires as soon as the app / browser window is closed
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if demo family exists
        context['has_demo_family'] = CustomUser.objects.filter(username='demo_familie').exists()
        return context

@require_POST
def load_demo_family_view(request):
    try:
        call_command('seed_demo_family')
        call_command('seed_target_groups')
        demo_accounts = [
            ('demo_familie', _('Familie (Standard)')),
            ('gering', _('Geringverdiener')),
            ('allein', _('Alleinerziehend')),
            ('student', _('Student')),
            ('rentner', _('Frührentner')),
        ]
        existing = [
            (uname, label)
            for uname, label in demo_accounts
            if CustomUser.objects.filter(username=uname).exists()
        ]
        if existing:
            list_items = format_html_join(
                '',
                '<li><strong>{}</strong> &ndash; {} ({}: <code>{}</code>)</li>',
                [(uname, label, _('Passwort'), uname) for uname, label in existing],
            )
            messages.success(
                request,
                format_html(
                    '<strong>{}</strong> ({}):<ul class="mb-0 mt-1 ps-3">{}</ul>',
                    _('Demo-Benutzer erfolgreich importiert'),
                    _('Passwort ist jeweils gleich dem Benutzernamen'),
                    list_items,
                ),
            )
        else:
            messages.error(request, _("Demo-Benutzer konnten nicht erstellt werden."))
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
    harmonies = DesignHarmony.objects.filter(is_active=True).order_by('order', 'id')
    return render(request, 'core/profile.html', {
        'form': form,
        'harmonies': harmonies,
    })

import json
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST
from .models import EditablePageContent
from .backup_service import generate_backup_archive, save_backup_to_directory

@login_required
def create_backup_view(request):
    """
    Creates a full backup (SQLite DB + Media files).
    If requested as download, returns the ZIP as attachment.
    If profile has a backup_path, writes the file there as well.
    """
    profile = request.user.profile
    download_requested = request.GET.get('download') == '1'

    saved_locally = False
    local_msg = ""
    if profile.backup_path:
        success, path, msg = save_backup_to_directory(profile.backup_path, max_keep=profile.backup_max_keep)
        saved_locally = success
        local_msg = msg

    # Update profile last run timestamp
    profile.backup_last_run = timezone.now()
    profile.backup_dismissed_until = None
    profile.save(update_fields=['backup_last_run', 'backup_dismissed_until'])

    if download_requested:
        buffer, filename, stats = generate_backup_archive()
        response = FileResponse(buffer, as_attachment=True, filename=filename)
        response['Content-Type'] = 'application/zip'
        return response

    if saved_locally:
        messages.success(request, _(f"Sicherung erfolgreich erstellt und gespeichert unter: {local_msg}"))
    else:
        messages.success(request, _("Sicherung wurde erfolgreich generiert."))

    return redirect(request.META.get('HTTP_REFERER', 'profile'))

@login_required
@require_POST
def dismiss_backup_warning_view(request):
    """
    Snoozes backup reminder for 7 days.
    """
    profile = request.user.profile
    profile.backup_dismissed_until = timezone.localdate() + datetime.timedelta(days=7)
    profile.save(update_fields=['backup_dismissed_until'])
    messages.info(request, _("Erinnerung an Datensicherung für 7 Tage stummgeschaltet."))
    return redirect(request.META.get('HTTP_REFERER', 'finance:dashboard'))

def get_page_content_map(page_name, lang='de'):
    qs = EditablePageContent.objects.filter(page=page_name, language=lang)
    return {item.section_key: item.content for item in qs}

@login_required
def help_view(request):
    lang = getattr(request, 'LANGUAGE_CODE', 'de')
    content_map = get_page_content_map('help', lang)
    if not content_map and lang != 'de':
        content_map = get_page_content_map('help', 'de')
    return render(request, 'core/help.html', {
        'content_map': content_map,
        'can_edit': request.user.is_superuser
    })

def about_view(request):
    lang = getattr(request, 'LANGUAGE_CODE', 'de')
    content_map = get_page_content_map('about', lang)
    if not content_map and lang != 'de':
        content_map = get_page_content_map('about', 'de')
    return render(request, 'core/about.html', {
        'content_map': content_map,
        'can_edit': request.user.is_authenticated and request.user.is_superuser
    })

@login_required
@require_POST
def save_page_content(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    try:
        data = json.loads(request.body)
        page = data.get('page')
        sections = data.get('sections', {})
        lang = data.get('language') or getattr(request, 'LANGUAGE_CODE', 'de')
        
        if page not in ('help', 'about'):
            return JsonResponse({'status': 'error', 'message': 'Invalid page'}, status=400)
            
        for key, val in sections.items():
            EditablePageContent.objects.update_or_create(
                page=page,
                section_key=key,
                language=lang,
                defaults={'content': val.strip()}
            )
        return JsonResponse({'status': 'ok', 'saved_keys': list(sections.keys())})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
