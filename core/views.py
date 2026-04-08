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
            return redirect('profile')
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
