import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponse
from unfold.admin import ModelAdmin
from unfold.decorators import action

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
    list_display = ('account_id', 'phone_number', 'first_name', 'email',)
    list_display_links = ('account_id', 'phone_number')
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=True)


# ==========================================
# 2. DRIVERS TABLE
# ==========================================
@admin.register(DriverAccount)
class DriverAccountAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ('account_id', 'phone_number', 'first_name', 'email', 'is_online', 'is_active',)
    list_display_links = ('account_id', 'phone_number')
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=False, role='driver')


# ==========================================
# 3. MECHANICS TABLE
# ==========================================
@admin.register(MechanicAccount)
class MechanicAccountAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ('account_id', 'phone_number', 'first_name', 'email', 'is_online', 'is_active')
    list_display_links = ('account_id', 'phone_number')
    readonly_fields = ('account_id',)
    
    ordering = ('id',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=False, role='mechanic')


# ==========================================
# 4. ASSISTANCE REQUESTS
# ==========================================
@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(ModelAdmin):
    list_display = ('row_number', 'driver', 'issue_type', 'status', 'mechanic', 'created_at')
    list_filter = ('status', 'issue_type')

    # Renders a standalone "Export CSV" button in Unfold's top header
    actions_list = ["export_all_csv"]

    @action(description="Export CSV", icon="download")
    def export_all_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="all_assistance_requests.csv"'
        
        writer = csv.writer(response)
        # Header Row
        writer.writerow([
            'ID', 
            'Driver Name', 
            'Driver Phone', 
            'Issue', 
            'License Plate', 
            'Assigned Mechanic', 
            'Mechanic Phone', 
            'Status', 
            'Created At'
        ])
        
        # Optimize queries by selecting mechanic along with driver and vehicle
        queryset = AssistanceRequest.objects.all().select_related('driver', 'mechanic', 'vehicle')
        
        for job in queryset:
            plate = job.vehicle.license_plate if job.vehicle else 'N/A'
            
            # Extract mechanic details dynamically
            if job.mechanic:
                mechanic_name = f"{job.mechanic.first_name} {job.mechanic.last_name}".strip() or job.mechanic.username
                mechanic_phone = getattr(job.mechanic, 'phone_number', 'N/A')
            else:
                mechanic_name = 'Unassigned'
                mechanic_phone = 'N/A'

            writer.writerow([
                job.id,
                f"{job.driver.first_name} {job.driver.last_name}".strip() or job.driver.username,
                getattr(job.driver, 'phone_number', 'N/A'),
                job.issue_type,
                plate,
                mechanic_name,
                mechanic_phone,
                job.status,
                job.created_at.strftime('%Y-%m-%d %H:%M')
            ])
            
        return response

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            cl = response.context_data['cl']
            for index, obj in enumerate(cl.result_list, start=1):
                obj.row_number = index
        except (AttributeError, KeyError):
            pass
        return response

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


# ==========================================
# 7. VEHICLES TABLE
# ==========================================
@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    list_display = ('license_plate', 'make', 'model', 'year', 'driver') 
    search_fields = ('license_plate', 'make', 'driver__username') 
    list_filter = ('year', 'make') 
    
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


# ==========================================
# 8. VERIFICATION DOCUMENTS TABLE
# ==========================================
@admin.register(VerificationDocument)
class VerificationDocumentAdmin(ModelAdmin):
    list_display = ('user', 'doc_type', 'is_approved', 'uploaded_at')
    list_filter = ('is_approved', 'doc_type')
    search_fields = ('user__username', 'user__email', 'user__first_name',)