from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin

from .models import (
    AdminProfile, 
    DriverAccount, 
    MechanicAccount, 
    AssistanceRequest, 
    Message, 
    UserLocation,
    Vehicle,
    VerificationDocument
)

# ==========================================
# 1. ADMINS TABLE
# ==========================================
@admin.register(AdminProfile)
class AdminProfileAdmin(BaseUserAdmin, ModelAdmin):
    # Displays the 5-character Alphanumeric ID instead of the default database row ID
    list_display = ('account_id', 'phone_number', 'first_name', 'email',)
    list_display_links = ('account_id', 'phone_number')
    
    # Required to force Django to display non-editable fields inside details panel
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    # Only show VIP Admins
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=True)


# ==========================================
# 2. DRIVERS TABLE
# ==========================================
@admin.register(DriverAccount)
class DriverAccountAdmin(BaseUserAdmin, ModelAdmin):
    # Displays the 5-character Alphanumeric ID instead of the default database row ID
    list_display = ('account_id', 'phone_number', 'first_name', 'email', 'is_online', 'is_active',)
    list_display_links = ('account_id', 'phone_number')
    
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    # Only show normal users who are Drivers
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=False, role='driver')


# ==========================================
# 3. MECHANICS TABLE
# ==========================================
@admin.register(MechanicAccount)
class MechanicAccountAdmin(BaseUserAdmin, ModelAdmin):
    # Displays the 5-character Alphanumeric ID instead of the default database row ID
    list_display = ('account_id', 'phone_number', 'first_name', 'email', 'is_online', 'is_active')
    list_display_links = ('account_id', 'phone_number')
    
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    # Only show normal users who are Mechanics
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=False, role='mechanic')


# ==========================================
# 4. ASSISTANCE REQUESTS (THE MIDDLEMAN)
# ==========================================
@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(ModelAdmin):
    # Replaced 'id' with 'row_number' to start counting rows smoothly from 1
    list_display = ('row_number', 'driver', 'issue_type', 'status', 'mechanic', 'created_at')
    list_filter = ('status', 'issue_type')

    # Intercepts dashboard generation to calculate index numbering sequence on the fly
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            cl = response.context_data['cl']
            # Enumerates items explicitly starting from number 1
            for index, obj in enumerate(cl.result_list, start=1):
                obj.row_number = index
        except (AttributeError, KeyError):
            pass
        return response

    # Defines the display layout options for our custom row numbering column header
    @admin.display(description='#')
    def row_number(self, obj):
        return getattr(obj, 'row_number', '-')


# ==========================================
# 5. MESSAGES TABLE
# ==========================================
@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ('sender', 'assistance_request', 'content', 'timestamp')
    list_filter = ('timestamp',)


# ==========================================
# 6. USER LOCATIONS TABLE
# ==========================================
@admin.register(UserLocation)
class UserLocationAdmin(ModelAdmin):
    list_display = ('user', 'get_user_type', 'latitude', 'longitude', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__username', 'user__email')

    @admin.display(description='User Type')
    def get_user_type(self, obj):
        if obj.user.groups.filter(name='Mechanic').exists():
            return "Mechanic"
        return "Driver"
    
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    # What shows up in the main table list
    list_display = ('license_plate', 'make', 'model', 'year', 'driver') 
    
    # Adds a search bar at the top
    search_fields = ('license_plate', 'make', 'driver__username') 
    
    # Adds a filter sidebar on the right
    list_filter = ('year', 'make') 
    
    # Groups the fields beautifully when adding/editing a vehicle
    fieldsets = (
        ('Driver Assignment', {
            'fields': ('driver',),
            'description': 'Select the driver this vehicle belongs to.'
        }),
        ('Vehicle Details', {
            'fields': ('make', 'model', 'year')
        }),
        ('Registration & Appearance', {
            'fields': ('license_plate', 'color')
        }),
    )


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'doc_type', 'is_approved', 'uploaded_at')
    list_filter = ('is_approved', 'doc_type')
    search_fields = ('user__username', 'user__email', 'user__first_name',)