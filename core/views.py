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
from .models import UserProfile, CustomUser, DesignHarmony, ChildProfile

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
            profile, _created = UserProfile.objects.get_or_create(user=user)
            if request.POST.get('accept_disclaimer') == 'on':
                profile.disclaimer_accepted_at = timezone.now()
                profile.disclaimer_version = '1.0'
                profile.save(update_fields=['disclaimer_accepted_at', 'disclaimer_version'])
            login(request, user)
            return redirect('finance:dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required
def toggle_night_mode(request):
    from .theme_engine import (
        MOODS,
        apply_theme_studio_to_profile,
        get_profile_theme_palette,
    )

    profile = request.user.profile
    dc = dict(profile.dashboard_config or {})
    raw_ts = dict(dc.get('theme_studio') or {}) if isinstance(dc.get('theme_studio'), dict) else {}
    palette = get_profile_theme_palette(profile)

    mood_key = raw_ts.get('mood', 'modern')
    if mood_key not in MOODS:
        mood_key = 'modern'
    current_bg_mode = raw_ts.get('bg_mode', 'auto')

    if palette.get('is_dark'):
        # Switch from Night -> Day: restore saved day_bg_mode ('light' or 'custom')
        day_mode = raw_ts.get('day_bg_mode', 'light')
        if day_mode not in ('auto', 'light', 'custom'):
            day_mode = 'light'
        if day_mode == 'auto' and MOODS[mood_key].get('dark'):
            day_mode = 'light'
        if day_mode == 'custom':
            custom_hex = raw_ts.get('bg_custom') or profile.background_color or '#ffffff'
            from .theme_engine import hex_to_hsl
            if hex_to_hsl(custom_hex)['l'] < 50:
                day_mode = 'light'
        raw_ts['bg_mode'] = day_mode
    else:
        # Switch from Day -> Night: remember current day mode, set bg_mode='dark'
        if current_bg_mode in ('auto', 'light', 'custom'):
            raw_ts['day_bg_mode'] = current_bg_mode
        else:
            raw_ts['day_bg_mode'] = 'light'
        raw_ts['bg_mode'] = 'dark'

    raw_ts.setdefault('mood', mood_key)
    raw_ts.setdefault('bg_custom', profile.background_color or '#ffffff')
    raw_ts.setdefault('sync_cards_and_charts', True)

    apply_theme_studio_to_profile(profile, raw_ts, manual_precision=False)
    profile.save()
    return redirect(request.META.get('HTTP_REFERER', 'profile'))

@login_required
def profile_view(request):
    from .theme_engine import (
        MOODS,
        CARD_SURFACES,
        BG_SVG_MODES,
        apply_theme_studio_to_profile,
        get_profile_theme_studio_settings,
        get_profile_theme_palette,
    )

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

            clean_overrides = {}
            raw_ov_str = request.POST.get('theme_state_overrides', '').strip()
            if raw_ov_str:
                try:
                    parsed_ov = json.loads(raw_ov_str)
                    if isinstance(parsed_ov, dict):
                        for k, v in parsed_ov.items():
                            ks = str(k).strip()
                            if ks in {'1', '2', '3', '4', '5', '6', '7', '8'}:
                                if isinstance(v, str):
                                    vs = v.strip().upper()
                                    if vs.startswith('#') and len(vs) in (4, 7):
                                        clean_overrides[ks] = vs
                                elif isinstance(v, dict):
                                    entry_ov = {}
                                    bg_v = v.get('bg')
                                    txt_v = v.get('text')
                                    if isinstance(bg_v, str) and bg_v.strip().startswith('#') and len(bg_v.strip()) in (4, 7):
                                        entry_ov['bg'] = bg_v.strip().upper()
                                    if isinstance(txt_v, str) and txt_v.strip().startswith('#') and len(txt_v.strip()) in (4, 7):
                                        entry_ov['text'] = txt_v.strip().upper()
                                    if entry_ov:
                                        clean_overrides[ks] = entry_ov
                except Exception:
                    pass

            dc = dict(prof.dashboard_config or {})
            prev_ts = dc.get('theme_studio', {}) if isinstance(dc.get('theme_studio'), dict) else {}
            card_surface = request.POST.get('theme_card_surface', prev_ts.get('card_surface', 'auto'))
            if card_surface not in CARD_SURFACES:
                card_surface = 'auto'
            bg_svg_mode = request.POST.get('theme_bg_svg_mode', prev_ts.get('bg_svg_mode', 'auto'))
            if bg_svg_mode not in BG_SVG_MODES:
                bg_svg_mode = 'auto'
            has_kpi_ext_fields = 'kpi_ext_present' in request.POST
            day_bg_mode = bg_mode if bg_mode != 'dark' else prev_ts.get('day_bg_mode', 'light')
            ts_payload = {
                'mood': mood,
                'bg_mode': bg_mode,
                'day_bg_mode': day_bg_mode,
                'bg_custom': bg_custom,
                'sync_cards_and_charts': sync_cards,
                'state_overrides': clean_overrides,
                'card_surface': card_surface,
                'bg_svg_mode': bg_svg_mode,
                'kpi_sparklines': (request.POST.get('kpi_sparklines') == 'on') if has_kpi_ext_fields else bool(prev_ts.get('kpi_sparklines', True)),
                'kpi_progress_bars': (request.POST.get('kpi_progress_bars') == 'on') if has_kpi_ext_fields else bool(prev_ts.get('kpi_progress_bars', True)),
                'kpi_watermarks': (request.POST.get('kpi_watermarks') == 'on') if has_kpi_ext_fields else bool(prev_ts.get('kpi_watermarks', True)),
                'kpi_spotlight': (request.POST.get('kpi_spotlight') == 'on') if has_kpi_ext_fields else bool(prev_ts.get('kpi_spotlight', True)),
                'kpi_click_navigation': (request.POST.get('kpi_click_navigation') == 'on') if has_kpi_ext_fields else bool(prev_ts.get('kpi_click_navigation', True)),
            }

            manual_precision = request.POST.get('theme_manual_precision') == '1'
            apply_theme_studio_to_profile(prof, ts_payload, manual_precision=manual_precision)
            prof.save()
            form.save_m2m()

            if 'children_json' in request.POST:
                raw_children = request.POST.get('children_json', '').strip()
                if raw_children:
                    try:
                        children_data = json.loads(raw_children)
                        if isinstance(children_data, list):
                            keep_ids = []
                            for c_item in children_data:
                                if not isinstance(c_item, dict):
                                    continue
                                c_name = str(c_item.get('name') or '').strip()
                                if not c_name:
                                    continue
                                c_id = c_item.get('id')
                                c_birth_str = str(c_item.get('birth_date') or '').strip()
                                c_birth = None
                                if c_birth_str:
                                    try:
                                        c_birth = datetime.datetime.strptime(c_birth_str, '%Y-%m-%d').date()
                                    except ValueError:
                                        pass
                                try:
                                    c_ind_age = int(c_item.get('expected_independence_age') or 21)
                                except (ValueError, TypeError):
                                    c_ind_age = 21
                                c_benefit = bool(c_item.get('receives_child_benefit', True))
                                child_obj = None
                                if c_id:
                                    child_obj = ChildProfile.objects.filter(user=request.user, id=c_id).first()
                                if not child_obj:
                                    child_obj = ChildProfile(user=request.user)
                                child_obj.name = c_name
                                child_obj.birth_date = c_birth
                                child_obj.expected_independence_age = c_ind_age
                                child_obj.receives_child_benefit = c_benefit
                                child_obj.save()
                                keep_ids.append(child_obj.id)
                            ChildProfile.objects.filter(user=request.user).exclude(id__in=keep_ids).delete()
                    except Exception:
                        pass

            messages.success(request, _("Profile updated successfully!"))
            return redirect('finance:dashboard')
    else:
        form = UserProfileForm(instance=profile)
    harmonies = DesignHarmony.objects.filter(is_active=True).order_by('order', 'id')
    available_shares = get_real_accessible_shares()
    is_same_vol = is_same_volume_as_app(profile.backup_path)
    in_docker = is_running_in_docker()
    has_external_mount = any(s.get('is_other_volume') for s in available_shares)

    user_children = list(ChildProfile.objects.filter(user=request.user).order_by('birth_date', 'id'))
    children_initial = [
        {
            'id': c.id,
            'name': c.name,
            'birth_date': c.birth_date.strftime('%Y-%m-%d') if c.birth_date else '',
            'expected_independence_age': c.expected_independence_age or 21,
            'receives_child_benefit': bool(c.receives_child_benefit),
        }
        for c in user_children
    ]

    ts_settings = get_profile_theme_studio_settings(profile)
    return render(request, 'core/profile.html', {
        'form': form,
        'harmonies': harmonies,
        'available_shares': available_shares,
        'is_same_volume': is_same_vol,
        'is_in_docker': in_docker,
        'has_external_mount': has_external_mount,
        'default_backup_dir': get_default_backup_dir(),
        'theme_studio': ts_settings,
        'theme_state_overrides_json': json.dumps(ts_settings.get('state_overrides', {})),
        'theme_palette': get_profile_theme_palette(profile),
        'children': user_children,
        'children_json': json.dumps(children_initial),
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


@login_required
@require_POST
def accept_legal_disclaimer_view(request):
    consent_no_advice = request.POST.get('consent_no_advice') == 'on'
    consent_security = request.POST.get('consent_security') == 'on'
    if not (consent_no_advice and consent_security):
        messages.error(request, _("Bitte bestätige beide Pflichtpunkte des rechtlichen & sicherheitstechnischen Hinweises."))
        return redirect(request.META.get('HTTP_REFERER', 'about'))

    profile, _created = UserProfile.objects.get_or_create(user=request.user)
    profile.disclaimer_accepted_at = timezone.now()
    profile.disclaimer_version = '1.0'
    profile.save(update_fields=['disclaimer_accepted_at', 'disclaimer_version'])
    messages.success(request, _("Rechtliche Hinweise & Sicherheitsregeln (Version 1.0) wurden erfolgreich bestätigt."))
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
