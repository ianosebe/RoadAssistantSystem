import json
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AssistanceRequest, Message, Vehicle, CustomUser
from .serializers import (
    RegisterSerializer,
    UserBasicSerializer,
    AssistanceRequestSerializer,
    MessageSerializer,
    VehicleSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email_or_phone = request.data.get('username')
        password = request.data.get('password')

        if not email_or_phone or not password:
            return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(
            Q(phone_number=email_or_phone) | Q(email=email_or_phone)
        ).first()

        if user and user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            login(request, user)
            return Response({'token': token.key, 'user': UserBasicSerializer(user).data})

        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class ObtainAuthTokenView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserBasicSerializer(request.user).data)


class AssistanceRequestListCreateView(generics.ListCreateAPIView):
    queryset = AssistanceRequest.objects.all().select_related('driver', 'mechanic')
    serializer_class = AssistanceRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'driver':
            return self.queryset.filter(driver=user)
        return self.queryset.filter(status='Pending')

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)


class AssistanceRequestDetailView(generics.RetrieveAPIView):
    queryset = AssistanceRequest.objects.all().select_related('driver', 'mechanic')
    serializer_class = AssistanceRequestSerializer


class AcceptRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        request_instance = get_object_or_404(AssistanceRequest, pk=pk, status='Pending')
        if request.user.role != 'mechanic':
            return Response({'detail': 'Only mechanics can accept requests.'}, status=status.HTTP_403_FORBIDDEN)

        request_instance.mechanic = request.user
        request_instance.status = 'Accepted'
        request_instance.save()
        return Response({'detail': 'Request accepted.'})


class CancelRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        request_instance = get_object_or_404(AssistanceRequest, pk=pk, driver=request.user)
        request_instance.status = 'Cancelled'
        request_instance.save()
        return Response({'detail': 'Request cancelled.'})


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(assistance_request_id=self.kwargs['pk']).select_related('sender')

    def perform_create(self, serializer):
        assistance_request = get_object_or_404(AssistanceRequest, pk=self.kwargs['pk'])
        serializer.save(sender=self.request.user, assistance_request=assistance_request)


class VehicleListCreateView(generics.ListCreateAPIView):
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(driver=self.request.user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)
