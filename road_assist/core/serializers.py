from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import serializers
from .models import CustomUser, AssistanceRequest, Message, Vehicle


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'first_name',
            'email',
            'phone_number',
            'role',
            'account_id',
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'email', 'phone_number', 'role', 'password']

    def validate_phone_number(self, value):
        if not value:
            raise serializers.ValidationError('Phone number is required.')
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Phone number is already registered.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(
            username=validated_data['phone_number'],
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user


class AssistanceRequestSerializer(serializers.ModelSerializer):
    driver = UserBasicSerializer(read_only=True)
    mechanic = UserBasicSerializer(read_only=True)

    class Meta:
        model = AssistanceRequest
        fields = [
            'id',
            'driver',
            'mechanic',
            'issue_type',
            'description',
            'latitude',
            'longitude',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context['request']
        return AssistanceRequest.objects.create(
            driver=request.user,
            status='Pending',
            **validated_data
        )


class MessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'assistance_request', 'sender', 'content', 'timestamp']
        read_only_fields = ['id', 'sender', 'timestamp', 'assistance_request']


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'make', 'model', 'year', 'license_plate', 'color']

    def create(self, validated_data):
        return Vehicle.objects.create(driver=self.context['request'].user, **validated_data)
