"""
URL configuration for road_assist project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core import views
from django.contrib.auth import views as auth_views
from django.conf import settings


urlpatterns = [
    path('api/', include('core.api_urls')),
    path('admin/', admin.site.urls),
    path('', views.splash_screen, name='splash'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('forgotpassword/', views.CustomPasswordResetView.as_view(), name='forgotpassword'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),


    # Dashboard URLs
    path('driver/', views.driver_home, name='driver_home'),
    path('mechanic/', views.mechanic_home, name='mechanic_home'),
    path('register/driver/', views.register_driver_view, name='register_driver'),
    path('register/mechanic/', views.register_mechanic_view, name='register_mechanic'),
    path('request-assistance/', views.request_assistance, name='request_assistance'),

    # API endpoints for request logic
    path('api/create-request/', views.create_assistance_request, name='create_request'),
    path('api/get-requests/', views.get_pending_requests, name='get_requests'),
    path('api/accept-request/', views.accept_assistance_request, name='accept_request'),
    path('accept-job/<int:request_id>/', views.accept_job, name='accept_job'),
    path('api/check-job-status/', views.check_job_status, name='check_job_status'),
    path('cancel-request/<int:request_id>/', views.cancel_request, name='cancel_request'),
    path('api/job/<int:job_id>/messages/', views.get_messages, name='get_messages'),
    path('api/job/<int:job_id>/send-message/', views.send_message, name='send_message'),
    path('api/job/<int:job_id>/messages/', views.get_messages, name='get_messages'),
    path('api/job/<int:job_id>/send-message/', views.send_message, name='send_message'),
    path('driver/', views.driver_home, name='driver_home'),
    path('history/', views.driver_history, name='driver_history'),
    path('settings/', views.driver_settings, name='driver_settings'),
    path('request/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('driver/services/', views.driver_services_view, name='driver_services'),
    path('driver/requests/', views.driver_requests_view, name='driver_requests'),
    path('driver/vehicles/', views.driver_vehicles_view, name='driver_vehicles'),
    path('driver/settings/', views.driver_settings_view, name='driver_settings'),
    path('settings/personal-info/', views.driver_personal_info, name='driver_personal_info'),
    path('settings/security/', views.driver_password_security, name='driver_password_security'),
    path('settings/license/', views.driver_license, name='driver_license'),
    path('settings/help/', views.driver_help_center, name='driver_help_center'),
    path('settings/privacy/', views.driver_privacy_policy, name='driver_privacy_policy'),
]

if settings.DEBUG:
    from django.conf import settings
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)