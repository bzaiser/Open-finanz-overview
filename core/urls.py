from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.AppLoginView.as_view(), name='home'),
    path('login/', views.AppLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('load-demo-family/', views.load_demo_family_view, name='load_demo_family'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/toggle-night/', views.toggle_night_mode, name='toggle_night_mode'),
    path('help/', views.help_view, name='help'),
    path('about/', views.about_view, name='about'),
    path('page-content/save/', views.save_page_content, name='save_page_content'),
]
