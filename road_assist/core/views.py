import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q, Avg


# Consolidated and cleaned up imports
from .models import CustomUser, AssistanceRequest, Message, Vehicle, VerificationDocument, MechanicProfile, Review, ServiceCategory


# ==========================================
# SPLASH & PASSWORD RESET
# ==========================================
class CustomPasswordResetView(PasswordResetView):
    template_name = 'core/forgotpassword.html'
    success_url = reverse_lazy('password_reset_done')

def splash_screen(request):
    return render(request, 'core/splash.html')


# ==========================================
# REGISTRATION LOGIC
# ==========================================
def register_driver_view(request):
    if request.method == 'POST':
        # CHANGED: Now explicitly grabbing 'first_name' to match the HTML form
        first_name = request.POST.get('first_name') 
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role') # Automatically catches 'driver' from the hidden field

        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect('register_driver')

        if CustomUser.objects.filter(phone_number=phone).exists():
            messages.error(request, 'This phone number is already registered.')
            return redirect('register_driver')

        # CHANGED: Passing the captured first_name variable into the database creation
        user = CustomUser.objects.create_user(
            username=phone, 
            email=email, 
            password=password, 
            phone_number=phone, 
            first_name=first_name, 
            role=role
        )
        
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('driver_home')

    return render(request, 'core/driver_register.html')

def register_mechanic_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role') # Automatically catches 'mechanic' from the hidden field

        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect('register_mechanic')

        if CustomUser.objects.filter(phone_number=phone).exists():
            messages.error(request, 'This phone number is already registered.')
            return redirect('register_mechanic')

        user = CustomUser.objects.create_user(username=phone, email=email, password=password, phone_number=phone, first_name=name, role=role)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('mechanic_home')

    return render(request, 'core/mechanic_register.html')


# ==========================================
# LOGIN & LOGOUT LOGIC
# ==========================================
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get('username')
        password = request.POST.get('password')
        
        user = None
        if login_input:
            # Safely fetch the user matching username, email, or phone number
            user_obj = CustomUser.objects.filter(
                Q(username__iexact=login_input) | 
                Q(email__iexact=login_input) | 
                Q(phone_number__iexact=login_input)
            ).first()
            
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            # Explicitly pass the custom backend
            login(request, user, backend='core.backends.EmailOrPhoneModelBackend')
            
            # --- ROLE-BASED REDIRECTION ---
            if user.role == 'mechanic':
                return redirect('mechanic_home') 
            elif user.role == 'admin':
                return redirect('admin:index')  
            else:
                return redirect('driver_home')  
                
        else:
            messages.error(request, "Invalid login credentials. Please check your details.")
            
    return render(request, 'core/login.html')

def logout_user(request):
    logout(request)
    return redirect('splash')


# ==========================================
# DASHBOARD VIEWS
# ==========================================
@login_required
def driver_home(request):
    active_job = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted']
    ).first()
    vehicles = []
    if request.user.is_authenticated:
        vehicles = Vehicle.objects.filter(driver=request.user)
    
    return render(request, 'core/driver_home.html', {
        'active_job': active_job,
        'vehicles': vehicles
    })

@login_required
def check_job_status(request, job_id):
    job = get_object_or_404(
        AssistanceRequest.objects.select_related('mechanic__mechanicprofile', 'mechanic__location'), 
        id=job_id
    )
    
    mechanic_name = None
    mechanic_phone = None
    mechanic_lat = None
    mechanic_lng = None

    if job.mechanic:
        mech = job.mechanic
        profile = getattr(mech, 'mechanicprofile', None)
        loc = getattr(mech, 'location', None)
        
        # 1. Resolve Mechanic Name
        first_name = getattr(mech, 'first_name', '')
        last_name = getattr(mech, 'last_name', '')
        if first_name or last_name:
            mechanic_name = f"{first_name} {last_name}".strip()
        elif profile and getattr(profile, 'shop_name', None):
            mechanic_name = profile.shop_name
        else:
            mechanic_name = str(mech)
            
        # 2. Resolve Phone Number across user model, profile, or location
        mechanic_phone = (
            getattr(mech, 'phone_number', None) or 
            getattr(profile, 'phone_number', None) or 
            getattr(loc, 'phone_number', None)
        )
        
        # 3. Resolve Coordinates with comprehensive fallbacks
        lat = (
            getattr(job, 'mechanic_lat', None) or 
            getattr(profile, 'latitude', None) or 
            getattr(loc, 'latitude', None) or 
            getattr(mech, 'latitude', None)
        )
        lng = (
            getattr(job, 'mechanic_lng', None) or 
            getattr(profile, 'longitude', None) or 
            getattr(loc, 'longitude', None) or 
            getattr(mech, 'longitude', None)
        )
        
        # Safely convert to float to prevent type errors
        try:
            mechanic_lat = float(lat) if lat is not None and lat != '' else None
        except (ValueError, TypeError):
            mechanic_lat = None
            
        try:
            mechanic_lng = float(lng) if lng is not None and lng != '' else None
        except (ValueError, TypeError):
            mechanic_lng = None

    return JsonResponse({
        'status': job.status, 
        'mechanic_name': mechanic_name,
        'mechanic_phone': mechanic_phone,
        'mechanic_lat': mechanic_lat,
        'mechanic_lng': mechanic_lng,
    })

@login_required
def mechanic_home(request):
    pending_jobs = AssistanceRequest.objects.filter(status='Pending', mechanic__isnull=True).select_related('driver')
    
    in_progress_jobs = AssistanceRequest.objects.filter(status='In Progress', mechanic=request.user).select_related('driver')
    accepted_jobs = AssistanceRequest.objects.filter(status='Accepted', mechanic=request.user).select_related('driver')
    
    cancelled_jobs = AssistanceRequest.objects.filter(status='Cancelled', mechanic=request.user).select_related('driver')
    completed_jobs = AssistanceRequest.objects.filter(status='Completed', mechanic=request.user).select_related('driver')
    
    context = {
        'pending_jobs': pending_jobs,
        'in_progress_jobs': in_progress_jobs,
        'accepted_jobs': accepted_jobs,
        'cancelled_jobs': cancelled_jobs,
        'completed_jobs': completed_jobs,
    }
    return render(request, 'core/mechanic_home.html', context)

# ==========================================
# ASSISTANCE REQUESTS (JSON / AJAX API)
# ==========================================
@login_required
def create_assistance_request(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        issue = data.get('issue_type')
        lat = data.get('latitude')
        lng = data.get('longitude')

        new_request = AssistanceRequest.objects.create(
            driver=request.user,
            issue_type=issue,
            latitude=lat,
            longitude=lng,
            status='Pending'
        )

        return JsonResponse({
            'status': 'success', 
            'message': 'Help is being requested!',
            'request_id': new_request.id
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@login_required
def get_pending_requests(request):
    if request.method == 'GET':
        pending_jobs = AssistanceRequest.objects.filter(status='Pending')
        
        jobs_data = []
        for job in pending_jobs:
            jobs_data.append({
                'id': job.id,
                'driver_name': job.driver.first_name,
                'driver_phone': job.driver.phone_number,
                'issue_type': job.issue_type,
                'latitude': job.latitude,
                'longitude': job.longitude,
                'time_requested': job.created_at.strftime("%H:%M")
            })

        return JsonResponse({'status': 'success', 'jobs': jobs_data})


@login_required
def accept_assistance_request(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        job_id = data.get('request_id')

        try:
            job = AssistanceRequest.objects.get(id=job_id, status='Pending')
            job.mechanic = request.user
            job.status = 'Accepted'
            job.save()

            return JsonResponse({'status': 'success', 'message': 'Job accepted!'})
        except AssistanceRequest.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Job no longer available.'})


# ==========================================
# ASSISTANCE REQUESTS (HTML Form Method)
# ==========================================
@login_required
def request_assistance(request):
    if request.method == 'POST':
        issue_type = request.POST.get('issue_type')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        raw_vehicle_id = request.POST.get('vehicle_id', '').strip()
        custom_make = request.POST.get('custom_make', '').strip()
        custom_plate = request.POST.get('custom_plate', '').strip()
        custom_year = request.POST.get('custom_year', '').strip()

        chosen_vehicle = None

        if raw_vehicle_id and raw_vehicle_id.isdigit():
            chosen_vehicle = get_object_or_404(Vehicle, id=raw_vehicle_id, driver=request.user)        
        elif custom_make and custom_plate:
            try:
                year_int = int(custom_year)
            except ValueError:
                year_int = 2026

            chosen_vehicle = Vehicle.objects.create(
                driver=request.user,
                make=custom_make,
                license_plate=custom_plate,
                year=year_int
            )
            messages.success(request, f"Added {custom_make} ({custom_plate}) to your registered garage!")

        # Safety net logic catches empty strings here
        if not chosen_vehicle:
            messages.error(request, "Error: Could not determine vehicle details. Please try again.")
            return redirect('driver_home')

        assistance_request = AssistanceRequest.objects.create(
            driver=request.user,
            issue_type=issue_type,
            latitude=latitude,
            longitude=longitude,
            vehicle=chosen_vehicle, 
            status='Pending'
        )

        return redirect('driver_home')
    


@login_required
def accept_job(request, request_id):
    job = get_object_or_404(AssistanceRequest, id=request_id)
    
    if request.method == 'POST':
        if job.status == 'Pending':
            # 1. Assign the mechanic and update status
            job.mechanic = request.user  
            job.status = 'Accepted'      
            
            # 2. Grab coordinates from the hidden inputs
            mechanic_lat = request.POST.get('mechanic_lat')
            mechanic_lng = request.POST.get('mechanic_lng')
            
            # 3. Save coordinates if they were successfully captured
            if mechanic_lat and mechanic_lng:
                try:
                    job.mechanic_lat = float(mechanic_lat)
                    job.mechanic_lng = float(mechanic_lng)
                except ValueError:
                    pass # Ignore if non-numeric data is accidentally sent
            
            job.save()
            messages.success(request, f"You've accepted the {job.issue_type} request!")
        else:
            messages.error(request, "Sorry, another mechanic already took this job!")

    return redirect('mechanic_home')


@login_required
def cancel_request(request, request_id):
    job = get_object_or_404(AssistanceRequest, id=request_id, driver=request.user)
    job.delete()
    
    messages.info(request, "Request cancelled. You can now select a new issue.")
    return redirect('driver_home')


@login_required
@require_GET
def get_messages(request, job_id):
    try:
        job = AssistanceRequest.objects.get(id=job_id)
        # Ensure messages are ordered chronologically
        messages = job.messages.all().order_by('timestamp')
        
        msg_list = []
        for msg in messages:
            msg_list.append({
                'content': msg.content,
                'is_mine': msg.sender == request.user, 
                'timestamp': msg.timestamp.strftime('%H:%M') if msg.timestamp else '', 
            })
            
        return JsonResponse({'status': 'success', 'messages': msg_list})
        
    except AssistanceRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Job not found'}, status=404)


@login_required
@require_POST
def send_message(request, job_id):
    try:
        job = AssistanceRequest.objects.get(id=job_id)
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if content:
            Message.objects.create(
                job=job,
                sender=request.user,
                content=content
            )
            return JsonResponse({'status': 'success'})
            
        return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'}, status=400)
        
    except AssistanceRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Job not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    
@login_required
def driver_history(request):
    past_jobs = AssistanceRequest.objects.filter(driver=request.user).order_by('-created_at')
    
    context = {
        'past_jobs': past_jobs
    }
    return render(request, 'core/driver_history.html', context)

@login_required
def driver_settings(request):
    license_doc = VerificationDocument.objects.filter(user=request.user, doc_type='LICENSE').first()
    
    context = {
        'license_doc': license_doc,
    }
    return render(request, 'core/driver_settings.html', context)

# ==========================================
# REJECT REQUEST 
# ==========================================
@login_required
def reject_request(request, request_id):
    assistance_request = get_object_or_404(AssistanceRequest, id=request_id)
    
    assistance_request.status = 'Pending'
    assistance_request.mechanic = None
    assistance_request.save()
    
    messages.success(request, "Request rejected. It is now available for other mechanics.")
    return redirect('mechanic_home')

@login_required
def driver_services_view(request):
    return render(request, 'core/driver_services.html')

@login_required
def driver_requests_view(request):
    # Fixed select_related to use 'mechanic__mechanicprofile' instead of 'mechanic__user'
    active_request = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted', 'In Progress', 'active']
    ).select_related('mechanic__mechanicprofile', 'vehicle').first()
    
    past_requests = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Completed', 'Cancelled']
    ).select_related('mechanic__mechanicprofile', 'vehicle').order_by('-created_at')
    
    total_count = AssistanceRequest.objects.filter(driver=request.user).count()

    context = {
        'active_request': active_request,
        'past_requests': past_requests,
        'total_count': total_count,
    }
    return render(request, 'core/driver_requests.html', context)

@login_required
def driver_vehicles_view(request):
    vehicles = Vehicle.objects.filter(driver=request.user).order_by('-id')
    
    context = {
        'vehicles': vehicles,
    }
    return render(request, 'core/driver_vehicles.html', context)

@login_required
def driver_settings_view(request):
    return render(request, 'core/driver_settings.html')

@login_required
def driver_personal_info(request):
    return render(request, 'core/driver_personal_info.html')

@login_required
def driver_password_security(request):
    return render(request, 'core/driver_password_security.html')

@login_required
def driver_license(request):
    return render(request, 'core/driver_license.html')

@login_required
def driver_help_center(request):
    return render(request, 'core/driver_help_center.html')

@login_required
def driver_privacy_policy(request):
    return render(request, 'core/driver_privacy_policy.html')

@login_required
def upload_license(request):
    if request.method == 'POST':
        front_file = request.FILES.get('license_front')
        back_file = request.FILES.get('license_back')

        if front_file:
            VerificationDocument.objects.update_or_create(
                user=request.user,
                doc_type='LICENSE',  
                defaults={
                    'document_image': front_file,           
                    'document_image_back': back_file,       
                    'is_approved': False                    
                }
            )
            messages.success(request, "License uploaded successfully! It is now pending review.")
            return redirect('driver_settings') 
            
        else:
            messages.error(request, "Please upload at least the front of your license.")

    return render(request, 'core/driver_license.html')

def car_towing(request):
    return render(request, 'core/car_towing.html')

@login_required
def car_towing_options_view(request):
    return render(request, 'core/car_towing.html')

@login_required
def car_towing_request_view(request):
    tier = request.GET.get('tier', 'half_down')
    
    pricing_map = {
        'half_down': {'name': 'Half-Down Towing', 'price': 75},
        'flatbed': {'name': 'Full-Down (Flatbed)', 'price': 95},
        'enclosed': {'name': 'Fully Enclosed', 'price': 150},
    }
    
    selected_service = pricing_map.get(tier, pricing_map['half_down'])
    user_vehicles = Vehicle.objects.filter(driver=request.user)

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        pickup_location = request.POST.get('pickup_location')
        destination = request.POST.get('destination')
        notes = request.POST.get('notes', '')
        
        # Capture real coordinates submitted from the form/frontend
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        
        # Compile textual/pricing data neatly into the description text field
        full_description = (
            f"Service Type: {selected_service['name']}\n"
            f"Estimated Base Cost: ${selected_service['price']}\n"
            f"Pickup Address: {pickup_location}\n"
            f"Dropoff Destination: {destination}\n"
            f"Driver Notes: {notes}"
        )
        
        # Safely grab the actual Vehicle database object instance
        vehicle_instance = None
        if vehicle_id:
            try:
                vehicle_instance = Vehicle.objects.get(id=vehicle_id, driver=request.user)
            except Vehicle.DoesNotExist:
                pass

        # Create the object with actual coordinates
        AssistanceRequest.objects.create(
            driver=request.user,
            issue_type='car_towing',  
            description=full_description,
            vehicle=vehicle_instance,
            latitude=float(lat) if lat and lat != '' else 0.0,
            longitude=float(lng) if lng and lng != '' else 0.0,
            status='Pending'
        )
        
        return redirect('driver_requests')

    context = {
        'selected_service': selected_service,
        'tier': tier,
        'vehicles': user_vehicles,
    }
    return render(request, 'core/car_towing_request.html', context)
def motorcycle_towing(request):
    return render(request, 'core/motorcycle_towing.html')

def boat_towing(request):
    return render(request, 'core/boat_towing.html')


# ==========================================
# ADD VEHICLE (HTML Form Handler)
# ==========================================
@login_required
def add_vehicle(request):
    if request.method == 'POST':
        make = request.POST.get('make', '').strip()
        model = request.POST.get('model', '').strip()
        year = request.POST.get('year', '').strip()
        license_plate = request.POST.get('license_plate', '').strip()

        if not (make and model and year and license_plate):
            messages.error(request, "All vehicle fields are required.")
            return redirect('driver_vehicles')

        Vehicle.objects.create(
            driver=request.user,  
            make=make,
            model=model,
            year=year,
            license_plate=license_plate
        )
        
        messages.success(request, "Vehicle added successfully to your garage!")
        return redirect('driver_vehicles')

    return redirect('driver_vehicles')

@login_required
def mechanic_activity(request):
    active_jobs = AssistanceRequest.objects.filter(mechanic=request.user, status='Accepted')
    history_jobs = AssistanceRequest.objects.filter(mechanic=request.user, status__in=['Completed', 'Cancelled'])
    
    try:
        reviews = Review.objects.filter(mechanic=request.user)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
        total_reviews = reviews.count()
    except NameError:
        reviews = []
        average_rating = 0.0
        total_reviews = 0
        
    context = {
        'active_jobs': active_jobs,
        'history_jobs': history_jobs,
        'reviews': reviews,
        'average_rating': round(average_rating, 1),
        'total_reviews': total_reviews,
    }
    return render(request, 'core/mechanic_activity.html', context)


@login_required
def mechanic_profile(request):
    try:
        mechanic_profile = request.user.mechanicprofile
    except MechanicProfile.DoesNotExist:
        mechanic_profile = None

    context = {
        'mechanic_profile': mechanic_profile,
    }
    return render(request, 'core/mechanic_profile.html', context)


@login_required
def complete_job(request, job_id):
    if request.method == 'POST':
        job = get_object_or_404(AssistanceRequest, id=job_id, mechanic=request.user)
        job.status = 'Completed'
        job.save()
    return redirect('mechanic_activity')

@login_required
def request_list_by_status(request, status):
    mechanic = request.user
    
    if status == 'pending':
        jobs = AssistanceRequest.objects.filter(status='pending').order_by('-created_at')
    elif status == 'active':
        jobs = AssistanceRequest.objects.filter(mechanic=mechanic, status__in=['accepted', 'in_progress']).order_by('-created_at')
    elif status == 'completed':
        jobs = AssistanceRequest.objects.filter(mechanic=mechanic, status='completed').order_by('-created_at')
    elif status == 'cancelled':
        jobs = AssistanceRequest.objects.filter(mechanic=mechanic, status='cancelled').order_by('-created_at')
    else:
        jobs = []

    context = {
        'jobs': jobs,
        'status_name': status.upper(),
        'status_slug': status
    }
    return render(request, 'core/request_list.html', context)

def api_pending_jobs(request):
    # Added select_related('vehicle') to optimize database queries
    jobs = AssistanceRequest.objects.filter(
        status='Pending', 
        mechanic__isnull=True
    ).select_related('driver', 'vehicle')
    
    data = []
    for job in jobs:
        # Check job.vehicle first; if null, check driver's first saved vehicle
        if job.vehicle:
            plate = job.vehicle.license_plate
        elif job.driver.vehicles.exists():
            plate = job.driver.vehicles.first().license_plate
        else:
            plate = 'N/A'

        data.append({
            'id': job.id,
            'issue_type': job.issue_type,
            'driver_name': f"{job.driver.first_name} {job.driver.last_name}".strip() or job.driver.phone_number,
            'driver_phone': job.driver.phone_number or 'N/A',
            'number_plate': plate,
            'latitude': job.latitude,
            'longitude': job.longitude,
            'created_at': "Just now" 
        })
    return JsonResponse({'pending_jobs': data})

def get_nearby_mechanics(request):
    driver_lat = request.GET.get('lat')
    driver_lng = request.GET.get('lng')

    if not driver_lat or not driver_lng:
        return JsonResponse({'status': 'error', 'message': 'Missing location data'}, status=400)

    mechanics = MechanicProfile.objects.filter(
        current_lat__isnull=False, 
        current_lng__isnull=False
    )
    
    mechanic_list = []
    for m in mechanics:
        mechanic_list.append({
            'id': m.id,
            'shop_name': getattr(m, 'shop_name', f"{m.user.username}'s Garage"),
            'latitude': float(m.current_lat),
            'longitude': float(m.current_lng),
        })

    return JsonResponse({'status': 'success', 'mechanics': mechanic_list})

@login_required
def battery_jumpstart_options_view(request):
    return render(request, 'core/battery_jumpstart.html')

@login_required
def battery_jumpstart_request_view(request):
    tier = request.GET.get('tier', 'jumpstart')
    
    pricing_map = {
        'jumpstart': {'name': 'Standard Jumpstart', 'price': 45},
        'replacement': {'name': 'New Battery & Install', 'price': 140},
    }
    
    selected_service = pricing_map.get(tier, pricing_map['jumpstart'])
    user_vehicles = Vehicle.objects.filter(driver=request.user)

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        location = request.POST.get('location')
        notes = request.POST.get('notes', '')
        
        full_description = (
            f"Service Type: {selected_service['name']}\n"
            f"Estimated Base Cost: ${selected_service['price']}\n"
            f"Location: {location}\n"
            f"Driver Notes: {notes}"
        )
        
        vehicle_instance = None
        if vehicle_id:
            try:
                vehicle_instance = Vehicle.objects.get(id=vehicle_id, driver=request.user)
            except Vehicle.DoesNotExist:
                pass

        # Use 'Battery Jumpstart' to map directly to your ISSUE_CHOICES
        AssistanceRequest.objects.create(
            driver=request.user,
            issue_type='Battery Jumpstart',
            description=full_description,
            vehicle=vehicle_instance,
            latitude=0.0,
            longitude=0.0,
            status='Pending'
        )
        
        return redirect('driver_requests')

    context = {
        'selected_service': selected_service,
        'tier': tier,
        'vehicles': user_vehicles,
    }
    return render(request, 'core/battery_jumpstart_request.html', context)

@login_required
def fuel_delivery_options_view(request):
    return render(request, 'core/fuel_delivery.html')

@login_required
def fuel_delivery_request_view(request):
    tier = request.GET.get('tier', 'regular')
    
    pricing_map = {
        'regular': {'name': 'Regular Unleaded', 'price_per_litre': 1.50},
        'premium': {'name': 'Premium Unleaded', 'price_per_litre': 1.80},
        'diesel': {'name': 'Diesel Fuel', 'price_per_litre': 1.60},
    }
    
    selected_service = pricing_map.get(tier, pricing_map['regular'])
    user_vehicles = Vehicle.objects.filter(driver=request.user)
    
    # Fetch available mechanics for the driver to choose from 
    # (Adjust filter if your project uses an explicit 'is_mechanic' boolean field)
    mechanics = MechanicProfile.objects.filter(user__isnull=False)

    # Check for any active request
    active_request = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted', 'In Progress', 'active']
    ).first()

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        mechanic_id = request.POST.get('mechanic_id')
        location = request.POST.get('location')
        notes = request.POST.get('notes', '')
        
        # 1. Grab Fuel Amount
        litres_str = request.POST.get('litres', '5')
        try:
            litres = float(litres_str)
        except ValueError:
            litres = 5.0
            
        # 2. Grab Driver GPS Coordinates
        lat_str = request.POST.get('latitude', '0.0')
        lng_str = request.POST.get('longitude', '0.0')
        
        try:
            latitude = float(lat_str)
            longitude = float(lng_str)
        except ValueError:
            latitude = 0.0
            longitude = 0.0
            
        # 3. Calculate upfront fuel cost only (delivery fee is calculated after acceptance)
        fuel_cost = litres * selected_service['price_per_litre']
        
        full_description = (
            f"Service Type: {selected_service['name']}\n"
            f"Fuel Requested: {litres} Litres\n"
            f"Estimated Fuel Cost: ${fuel_cost:.2f}\n"
            f"Location Notes: {location}\n"
            f"Driver Notes: {notes}"
        )
        
        vehicle_instance = None
        if vehicle_id:
            try:
                vehicle_instance = Vehicle.objects.get(id=vehicle_id, driver=request.user)
            except Vehicle.DoesNotExist:
                pass

        mechanic_instance = None
        if mechanic_id:
            try:
                mechanic_instance = MechanicProfile.objects.get(id=mechanic_id)
            except MechanicProfile.DoesNotExist:
                pass

        AssistanceRequest.objects.create(
            driver=request.user,
            mechanic=mechanic_instance,
            issue_type='Fuel Delivery',
            description=full_description,
            vehicle=vehicle_instance,
            latitude=latitude,
            longitude=longitude,
            status='Pending'
        )
        
        return redirect('driver_requests')

    context = {
        'selected_service': selected_service,
        'tier': tier,
        'vehicles': user_vehicles,
        'mechanics': mechanics,
        'active_request': active_request,
    }
    return render(request, 'core/fuel_delivery_request.html', context)


@login_required
def mechanic_specializations_view(request):
    # 1. Access the profile safely using the lowercase 'mechanicprofile' relation
    mechanic_profile, created = MechanicProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # 2. Grab the list of checked values from the form
        selected_specs = request.POST.getlist('specializations')
        
        # 3. Join them into a comma-separated string to save into your CharField
        mechanic_profile.specialization = ", ".join(selected_specs)
        mechanic_profile.save()
        
        return redirect('mechanic_profile')

    # Hardcoded master list of service options to fuel your HTML checklist
    all_services = [
        {
            'id': 'Engine Diagnostics', 
            'name': 'Engine Diagnostics', 
            'description': 'Tune-ups, overhauls, and check engine lights.',
            'icon_class': 'fa-solid fa-gauge-high'
        },
        {
            'id': 'Brakes & Suspension', 
            'name': 'Brakes & Suspension', 
            'description': 'Brake pads, rotors, alignments, and shocks.',
            'icon_class': 'fa-solid fa-car-burst'
        },
        {
            'id': 'Electrical Repair', 
            'name': 'Electrical Repair', 
            'description': 'Batteries, alternators, starters, and wiring.',
            'icon_class': 'fa-solid fa-bolt'
        },
        {
            'id': 'Emergency Towing', 
            'name': 'Emergency Towing', 
            'description': 'Roadside extraction and vehicle transport.',
            'icon_class': 'fa-solid fa-truck-pickup'
        },
    ]

    # 4. Break the comma-separated string back into a Python list for the template check
    if mechanic_profile.specialization:
        current_specializations = [s.strip() for s in mechanic_profile.specialization.split(',')]
    else:
        current_specializations = []

    context = {
        'all_services': all_services,
        'current_specializations': current_specializations,
    }
    return render(request, 'core/mechanic_specialization.html', context)

def cancel_job_api(request, job_id):
    if request.method == 'POST':
        job = get_object_or_404(AssistanceRequest, id=job_id)
        job.status = 'Cancelled'
        job.save()
        return JsonResponse({'status': 'success', 'message': 'Job successfully cancelled.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

