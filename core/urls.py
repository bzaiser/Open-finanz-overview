from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='core/login.html', redirect_authenticated_user=True), name='home'), # Redirect or root
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/toggle-night/', views.toggle_night_mode, name='toggle_night_mode'),
    path('help/', views.help_view, name='help'),
    path('about/', views.about_view, name='about'),
]
