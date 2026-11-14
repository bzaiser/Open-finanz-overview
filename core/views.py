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
    from .theme_engine import (
        MOODS,
        compute_theme_palette,
        get_profile_theme_studio_settings,
        get_profile_theme_palette,
    )
    from finance.card_registry import apply_theme_palette_to_cards

    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            prof = form.save(commit=False)

            mood = request.POST.get('theme_mood', 'modern')
            if mood not in MOODS:
                mood = 'modern'
            bg_mode = request.POST.get('theme_bg_mode', 'auto')
            if bg_mode not in ('auto', 'light', 'dark', 'custom'):
                bg_mode = 'auto'
            bg_custom = request.POST.get('theme_bg_custom') or prof.background_color or '#ffffff'
            sync_cards = request.POST.get('theme_sync_cards') == 'on'

            dc = dict(prof.dashboard_config or {})
            dc['theme_studio'] = {
                'mood': mood,
                'bg_mode': bg_mode,
                'bg_custom': bg_custom,
                'sync_cards_and_charts': sync_cards,
            }

            palette = compute_theme_palette(
                c1=prof.gradient_start or '#6610f2',
                c2=prof.gradient_end or '#0d6efd',
                mood_key=mood,
                bg_mode=bg_mode,
                bg_custom=bg_custom,
            )

            if sync_cards:
                dc = apply_theme_palette_to_cards(dc, palette)

            prof.dashboard_config = dc
            prof.save()
            form.save_m2m()
            messages.success(request, _("Profile updated successfully!"))
            return redirect('finance:dashboard')
    else:
        form = UserProfileForm(instance=profile)
    harmonies = DesignHarmony.objects.filter(is_active=True).order_by('order', 'id')
    available_shares = get_real_accessible_shares()
    is_same_vol = is_same_volume_as_app(profile.backup_path)
    in_docker = is_running_in_docker()
    has_external_mount = any(s.get('is_other_volume') for s in available_shares)

    return render(request, 'core/profile.html', {
        'form': form,
        'harmonies': harmonies,
        'available_shares': available_shares,
        'is_same_volume': is_same_vol,
        'is_in_docker': in_docker,
        'has_external_mount': has_external_mount,
        'default_backup_dir': get_default_backup_dir(),
        'theme_studio': get_profile_theme_studio_settings(profile),
        'theme_palette': get_profile_theme_palette(profile),
    })

import os
import json
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST
from .models import EditablePageContent
from .backup_service import (
    start_background_backup,
    get_job_status,
    get_real_accessible_shares,
    get_default_backup_dir,
    is_same_volume_as_app,
    test_directory_writable,
    is_running_in_docker
)

@login_required
def create_backup_view(request):
    """
    Starts asynchronous backup task writing directly to user's configured backup_path (or default data/backups).
    If custom_path is passed in POST, saves it immediately to the profile.
    If called via AJAX / POST, returns JSON with job_id for progress monitoring.
    """
    profile = request.user.profile

    # If the user changed the backup path in the input field before clicking 'execute', apply and save it immediately
    if request.method == 'POST':
        custom_path = request.POST.get('custom_path')
        if custom_path is not None:
            clean_p = custom_path.strip() or None
            if clean_p:
                if not os.path.isabs(clean_p):
                    return JsonResponse({'status': 'error', 'message': _("Bitte einen absoluten Pfad angeben.")}, status=400)
                writable, err_msg = test_directory_writable(clean_p)
                if not writable:
                    return JsonResponse({'status': 'error', 'message': _(f"Keine Schreibrechte im Pfad: {err_msg}")}, status=400)
            profile.backup_path = clean_p
            profile.save(update_fields=['backup_path'])

    try:
        job_id, target_dir = start_background_backup(profile)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.method == 'POST':
            return JsonResponse({
                'status': 'started',
                'job_id': job_id,
                'target_directory': target_dir
            })
        messages.info(request, _("Datensicherung im Hintergrund gestartet."))
        return redirect(request.META.get('HTTP_REFERER', 'profile'))
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.method == 'POST':
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        messages.error(request, _(f"Fehler beim Starten der Sicherung: {e}"))
        return redirect(request.META.get('HTTP_REFERER', 'profile'))

@login_required
def backup_progress_view(request, job_id):
    """
    Returns JSON progress of running backup job.
    """
    job = get_job_status(job_id)
    if not job:
        return JsonResponse({'status': 'not_found', 'message': _("Job nicht gefunden.")}, status=404)

    return JsonResponse({
        'job_id': job['id'],
        'status': job['status'],
        'progress': job['progress'],
        'step_label': job.get('step_label', ''),
        'target_file': job.get('target_file', ''),
        'filename': job.get('filename', ''),
        'file_size_mb': job.get('file_size_mb', 0),
        'download_url': f"/profile/backup/download/{job['id']}/" if job.get('status') == 'completed' else None,
        'error': job.get('error', None)
    })

@login_required
def download_backup_file_view(request, job_id):
    """
    Direct browser download of completed backup zip file.
    """
    job = get_job_status(job_id)
    if not job or job.get('status') != 'completed' or not job.get('target_file'):
        messages.error(request, _("Backup-Datei nicht gefunden oder noch nicht fertig."))
        return redirect('profile')

    target_file = job['target_file']
    if not os.path.exists(target_file):
        messages.error(request, _("Datei auf dem Server nicht mehr vorhanden."))
        return redirect('profile')

    filename = job.get('filename') or os.path.basename(target_file)
    return FileResponse(open(target_file, 'rb'), as_attachment=True, filename=filename)

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
