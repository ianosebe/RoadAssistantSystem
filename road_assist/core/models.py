import string
import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def generate_unique_account_id(model_class):
    """Generates a random 5-character uppercase alphanumeric string and ensures it's unique."""
    chars = string.ascii_uppercase + string.digits # A-Z and 0-9
    while True:
        new_id = ''.join(secrets.choice(chars) for _ in range(5))
        # Ensure this ID doesn't already exist in the database
        if not model_class.objects.filter(account_id=new_id).exists():
            return new_id


# ==========================================
# CORE USER MODEL
# ==========================================
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('driver', 'Driver'),
        ('mechanic', 'Mechanic'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, unique=True, blank=False, null=False)
    
    # Custom 5-Character Alphanumeric ID
    account_id = models.CharField(max_length=5, unique=True, editable=False, blank=True, null=True)

    REQUIRED_FIELDS = ['email', 'phone_number']
    
    # Driver specific
    vehicle_details = models.CharField(max_length=100, blank=True, null=True)
    is_online = models.BooleanField(default=False)

    # Automatically generate the account_id when saving a new user
    def save(self, *args, **kwargs):
        if not self.account_id:
            self.account_id = generate_unique_account_id(self.__class__)
        super().save(*args, **kwargs)

    # 1. This changes how the user looks in database lists
    def __str__(self):
        # If they have a name, show it. Otherwise, show phone.
        if self.first_name:
            return self.first_name
        return self.phone_number

    # 2. This specifically changes the "WELCOME, X" text in the top right corner!
    def get_short_name(self):
        if self.first_name:
            return self.first_name
        return self.phone_number


class MechanicProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Mechanic Profile: {self.user.username}"

# ==========================================
# PROXY MODELS FOR ADMIN PANEL
# ==========================================
class AdminProfile(CustomUser):
    class Meta:
        proxy = True
        verbose_name = 'Admin Account'
        verbose_name_plural = 'Admin Accounts'

class DriverAccount(CustomUser):
    class Meta:
        proxy = True 
        verbose_name = 'Driver Account'
        verbose_name_plural = 'Driver Accounts'

class MechanicAccount(CustomUser):
    class Meta:
        proxy = True 
        verbose_name = 'Mechanic Account'
        verbose_name_plural = 'Mechanic Accounts'


# ==========================================
# ASSISTANCE REQUESTS & MESSAGES
# ==========================================
class AssistanceRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),      # Driver requested, waiting for a mechanic
        ('Accepted', 'Accepted'),    # Mechanic is on the way
        ('Completed', 'Completed'),  # Job is done
        ('Cancelled', 'Cancelled'),  # Driver or Mechanic cancelled
    )

    ISSUE_CHOICES = (
        ('Flat Tire', 'Flat Tire'),
        ('Dead Battery', 'Dead Battery'),
        ('Engine Overheating', 'Engine Overheating'),
        ('Out of Gas', 'Out of Gas'),
        ('Lockout', 'Lockout'),
        ('Winch Out', 'Winch Out'),
        ('Tire Repair', 'Tire Repair'),
        ('Other', 'Other'),
    )

    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests_made')
    mechanic = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs_accepted')
    
    issue_type = models.CharField(max_length=50, choices=ISSUE_CHOICES)
    description = models.TextField(blank=True, null=True) 

    vehicle = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Driver's breakdown location coordinates
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Mechanic tracking coordinates
    mechanic_lat = models.FloatField(null=True, blank=True)
    mechanic_lng = models.FloatField(null=True, blank=True)
    
    # --- ADDED: Fuel specific fields ---
    fuel_litres = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.issue_type} for {self.driver.first_name} - {self.status}"

class Message(models.Model):
    assistance_request = models.ForeignKey(
        'AssistanceRequest', 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender} at {self.timestamp.strftime('%H:%M')}"
    

# ==========================================
# ONLINE STATUS SIGNALS
# ==========================================
# 1. When Django announces a user logged in, flip CustomUser's is_online to True
@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    user.is_online = True
    user.save(update_fields=['is_online']) # update_fields makes the database save much faster

# 2. When Django announces a user logged out, flip CustomUser's is_online to False
@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    user.is_online = False
    user.save(update_fields=['is_online'])


# ==========================================
# GPS TRACKING
# ==========================================
class UserLocation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location')
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Location"
        verbose_name_plural = "User Locations"

    def __str__(self):
        return f"{self.user.username}'s Location ({self.latitude}, {self.longitude})"
    

class Vehicle(models.Model):
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50, help_text="e.g., Toyota, Honda")
    model = models.CharField(max_length=50, help_text="e.g., Camry, Civic")
    year = models.IntegerField()
    license_plate = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=30, blank=True, null=True, help_text="Hex code or color name")

    def __str__(self):
        return f"{self.make} {self.model} ({self.license_plate})"
    

class VerificationDocument(models.Model):
    # A dropdown list of choices for what type of document this is
    DOCUMENT_TYPES = (
        ('ID_CARD', 'National ID Card'),
        ('LICENSE', 'Driver License'),
        ('CERTIFICATE', 'Mechanic Certification'),
        ('CAR_REG', 'Vehicle Registration'),
    )
    
    # Link the document to a specific user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verification_docs')
    
    # What type of document is this?
    doc_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    
    # The actual image file. It will upload to a folder like: media/verifications/2026/05/
    document_image = models.ImageField(upload_to='verifications/%Y/%m/')
    document_image_back = models.ImageField(upload_to='verifications/back/%Y/%m/', blank=True, null=True)
    
    # Has an admin checked and approved this document?
    is_approved = models.BooleanField(default=False)
    
    # When was it uploaded?
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_doc_type_display()}"



class Review(models.Model):
    assistance_request = models.OneToOneField(AssistanceRequest, on_delete=models.CASCADE, related_name='review')
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')
    mechanic = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.IntegerField(default=5) # 1 to 5 stars
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.mechanic.username} by {self.driver.username} - {self.rating}★"


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='service_icons/', blank=True, null=True)

    def __str__(self):
        return self.name