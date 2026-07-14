from django.urls import path
from . import api_views

urlpatterns = [
    path('auth/register/', api_views.RegisterView.as_view(), name='api_register'),
    path('auth/login/', api_views.LoginView.as_view(), name='api_login'),
    path('auth/logout/', api_views.LogoutView.as_view(), name='api_logout'),
    path('auth/token/', api_views.ObtainAuthTokenView.as_view(), name='api_token'),

    path('requests/', api_views.AssistanceRequestListCreateView.as_view(), name='api_requests'),
    path('requests/<int:pk>/', api_views.AssistanceRequestDetailView.as_view(), name='api_request_detail'),
    path('requests/<int:pk>/accept/', api_views.AcceptRequestView.as_view(), name='api_request_accept'),
    path('requests/<int:pk>/cancel/', api_views.CancelRequestView.as_view(), name='api_request_cancel'),
    path('requests/<int:pk>/messages/', api_views.MessageListCreateView.as_view(), name='api_request_messages'),

    path('vehicles/', api_views.VehicleListCreateView.as_view(), name='api_vehicles'),
    path('profile/', api_views.UserProfileView.as_view(), name='api_profile'),
]