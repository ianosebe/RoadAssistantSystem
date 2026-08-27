"""
URL configuration for road_assist project.
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
    path('mechanic/activity/', views.mechanic_activity, name='mechanic_activity'),
    path('mechanic/profile/', views.mechanic_profile, name='mechanic_profile'),
    path('requests/status/<str:status>/', views.request_list_by_status, name='request_list_by_status'),
    path('profile/personal-info/', views.driver_personal_info, name='personal_info'),
    path('profile/help/', views.driver_help_center, name='driver_help_center'),
    path('profile/privacy/', views.driver_privacy_policy, name='driver_privacy_policy'),
    path('mechanic/specialization/', views.mechanic_specializations_view, name='mechanic_specialization'),

    # Driver Towing Services
    path('driver/motorcycle_towing/', views.motorcycle_towing, name='motorcycle_towing'),
    path('driver/boat_towing/', views.boat_towing, name='boat_towing'),
    path('services/car-towing/', views.car_towing_options_view, name='car_towing'),
    path('services/car-towing/request/', views.car_towing_request_view, name='car_towing_request'),
    path('services/battery-jumpstart/', views.battery_jumpstart_options_view, name='battery_jumpstart'),
    path('services/battery-jumpstart/request/', views.battery_jumpstart_request_view, name='battery_jumpstart_request'),
    path('services/fuel-delivery/', views.fuel_delivery_options_view, name='fuel_delivery'),
    path('services/fuel-delivery/request/', views.fuel_delivery_request_view, name='fuel_delivery_request'),
    
    # New Services
    path('services/lockout/', views.lockout_options_view, name='lockout'),
    path('services/lockout/request/', views.lockout_request_view, name='lockout_request'),
    path('services/winch-out/', views.winch_out_options_view, name='winch_out'),
    path('services/winch-out/request/', views.winch_out_request_view, name='winch_out_request'),
    path('services/tire-repair/', views.tire_repair_options_view, name='tire_repair'),
    path('services/tire-repair/request/', views.tire_repair_request_view, name='tire_repair_request'),
    

    # API endpoints for request logic
    path('api/create-request/', views.create_assistance_request, name='create_request'),
    path('api/get-requests/', views.get_pending_requests, name='get_requests'),
    path('api/accept-request/', views.accept_assistance_request, name='accept_request'),
    path('accept-job/<int:request_id>/', views.accept_job, name='accept_job'),
    path('api/check-job-status/<int:job_id>/', views.check_job_status, name='check_job_status'),   
    path('cancel-request/<int:request_id>/', views.cancel_request, name='cancel_request'),
    path('api/job/<int:job_id>/messages/', views.get_messages, name='get_messages'),
    path('api/job/<int:job_id>/send-message/', views.send_message, name='send_message'),
    path('request/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('mechanic/job/<int:job_id>/complete/', views.complete_job, name='complete_job'),
    path('api/pending-jobs/', views.api_pending_jobs, name='api_pending_jobs'),
    path('api/job/<int:job_id>/cancel/', views.cancel_job_api, name='cancel_job_api'),

    # Driver specific views
    path('history/', views.driver_history, name='driver_history'),
    path('driver/services/', views.driver_services_view, name='driver_services'),
    path('driver/requests/', views.driver_requests_view, name='driver_requests'),
    path('api/nearby-mechanics/', views.get_nearby_mechanics, name='nearby_mechanics'),
    
    # Vehicles (Replaced the API view with the standard HTML view)
    path('driver/vehicles/', views.driver_vehicles_view, name='driver_vehicles'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),

    # Driver Settings
    path('settings/', views.driver_settings, name='driver_settings'),
    path('settings/personal-info/', views.driver_personal_info, name='driver_personal_info'),
    path('settings/security/', views.driver_password_security, name='driver_password_security'),
    path('settings/license/', views.driver_license, name='driver_license'),
    path('settings/help/', views.driver_help_center, name='driver_help_center'),
    path('settings/privacy/', views.driver_privacy_policy, name='driver_privacy_policy'),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)