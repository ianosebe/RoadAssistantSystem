import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from .models import AssistanceRequest
from .models import Vehicle
from .models import VerificationDocument

# Ensure these match the exact names in your models.py
from .models import CustomUser, AssistanceRequest, Message

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
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role') # Automatically catches 'driver' from the hidden field

        user = CustomUser.objects.create_user(username=phone, email=email, password=password, phone_number=phone, first_name=name, role=role)
        login(request, user)
        return redirect('driver_home')

    return render(request, 'core/driver_register.html')

def register_mechanic_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role') # Automatically catches 'mechanic' from the hidden field

        user = CustomUser.objects.create_user(username=phone, email=email, password=password, phone_number=phone, first_name=name, role=role)
        login(request, user)
        return redirect('mechanic_home')

    return render(request, 'core/mechanic_register.html')


# ==========================================
# LOGIN & LOGOUT LOGIC
# ==========================================
def login_view(request):
    if request.method == 'POST':
        username_input = request.POST.get('username')  # This could be an email or a phone number
        password_input = request.POST.get('password')

        # 1. Look up the user by phone_number OR email in the database
        try:
            user_obj = CustomUser.objects.get(Q(phone_number=username_input) | Q(email=username_input))
            # Treat whatever is in their 'username' field (the phone number) as the login identifier
            login_username = user_obj.username
        except CustomUser.DoesNotExist:
            # If no user matches, pass the raw input so authenticate() handles the failure safely
            login_username = username_input

        # 2. Check if the credentials match the database
        user = authenticate(request, username=login_username, password=password_input)

        if user is not None:
            # 3. Log them in!
            login(request, user)
            
            # 4. Redirect based on role
            if user.role == 'mechanic':
                return redirect('mechanic_home')  
            else:
                return redirect('driver_home')    
                
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'core/login.html')

def logout_user(request):
    logout(request)
    return redirect('splash')


# ==========================================
# DASHBOARD VIEWS
# ==========================================
@login_required
def driver_home(request):
    # ONLY find jobs that are actually live. 
    # If it's deleted, this returns None. 
    # If you use 'Cancelled' status, this excludes it.
    active_job = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted']
    ).first()
    
    return render(request, 'core/driver_home.html', {
        'active_job': active_job
    })

# Add this NEW function so the browser can ask "Has anyone accepted yet?"
@login_required
def check_job_status(request):
    # Look for the current active job for this driver
    job = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted']
    ).first()
    
    if job:
        # If a mechanic has accepted, send 'Accepted' + Mechanic details
        if job.status == 'Accepted' and job.mechanic:
            return JsonResponse({
                'status': 'Accepted',
                'mechanic_name': job.mechanic.first_name,
                'mechanic_phone': job.mechanic.phone_number if job.mechanic.phone_number else "No phone provided",
                'issue': job.issue_type
            })
        
        # Otherwise, tell the UI it's still pending
        return JsonResponse({'status': 'Pending'})
    
    # If the job was deleted/cancelled, tell the UI to reset
    return JsonResponse({'status': 'None'})

@login_required
def mechanic_home(request):
    # ADD .select_related('driver') TO YOUR QUERYSETS!
    pending_jobs = AssistanceRequest.objects.filter(status='Pending', mechanic__isnull=True).select_related('driver')
    in_progress_jobs = AssistanceRequest.objects.filter(status='In Progress').select_related('driver')
    accepted_jobs = AssistanceRequest.objects.filter(status='Accepted').select_related('driver')
    cancelled_jobs = AssistanceRequest.objects.filter(status='Cancelled').select_related('driver')
    completed_jobs = AssistanceRequest.objects.filter(status='Completed').select_related('driver')
    
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
        # Read the hidden data sent from the Driver's phone/browser
        data = json.loads(request.body)
        issue = data.get('issue_type')
        lat = data.get('latitude')
        lng = data.get('longitude')

        # Create the new job in the database
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
        # Find all requests that haven't been accepted yet
        pending_jobs = AssistanceRequest.objects.filter(status='Pending')
        
        # Package them up into a list to send to the Mechanic's map
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
            # Find the specific job in the database
            job = AssistanceRequest.objects.get(id=job_id, status='Pending')
            
            # Update it: Assign this mechanic and mark it accepted!
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
        issue = request.POST.get('issue_type')
        
        # Create the new job ticket in the database
        # We pass empty strings to latitude and longitude to fix the IntegrityError!
        AssistanceRequest.objects.create(
            driver=request.user,
            issue_type=issue,
            status='Pending',
            latitude="0.0",   
            longitude="0.0"   
        )
        
        messages.success(request, f"Your {issue} request has been sent to nearby mechanics!")
        return redirect('driver_home') # Send them back to the map
    
@login_required
def accept_job(request, request_id):
    # 1. Find the specific job or show a 404 error if it doesn't exist
    job = get_object_or_404(AssistanceRequest, id=request_id)
    
    # 2. Safety check: only accept if it's still 'Pending'
    if job.status == 'Pending':
        job.mechanic = request.user  # Assign the current mechanic
        job.status = 'Accepted'      # Update status
        job.save()
        messages.success(request, f"You've accepted the {job.issue_type} request!")
    else:
        messages.error(request, "Sorry, another mechanic already took this job!")

    # 3. Stay on the dashboard to see updated stats
    return redirect('mechanic_home')


@login_required
def cancel_request(request, request_id):
    # Find the job belonging to this driver
    job = get_object_or_404(AssistanceRequest, id=request_id, driver=request.user)
    
    # We only allow cancelling if a mechanic hasn't started driving yet (optional)
    # For now, let's just delete it so they can start over
    job.delete()
    
    messages.info(request, "Request cancelled. You can now select a new issue.")
    return redirect('driver_home')

@login_required
@require_GET
def get_messages(request, job_id):
    """
    Fetches all messages for a specific job and sends them back as JSON.
    """
    try:
        # Fetch the active job (change AssistanceRequest to your model name)
        job = AssistanceRequest.objects.get(id=job_id)
        
        # Get all messages tied to this job
        messages = job.messages.all()
        
        msg_list = []
        for msg in messages:
            msg_list.append({
                'content': msg.content,
                # is_mine is True if the logged-in user sent it (makes the bubble blue on the right)
                'is_mine': msg.sender == request.user, 
                # Format time as '14:30'
                'timestamp': msg.timestamp.strftime('%H:%M'), 
            })
            
        return JsonResponse({'status': 'success', 'messages': msg_list})
        
    except AssistanceRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Job not found'}, status=404)


@login_required
@require_POST
def send_message(request, job_id):
    """
    Receives a new message from the frontend and saves it to the database.
    """
    try:
        job = AssistanceRequest.objects.get(id=job_id)
        
        # Parse the JSON sent by the JavaScript fetch() request
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if content:
            # Save to database
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
    # Fetch all jobs for this user, ordered by newest first
    # Adjust 'driver' to match whatever your user foreign key is named in the model
    past_jobs = AssistanceRequest.objects.filter(driver=request.user).order_by('-created_at')
    
    context = {
        'past_jobs': past_jobs
    }
    return render(request, 'core/driver_history.html', context)

@login_required
def driver_settings(request):
    # We will build the full settings logic later!
    license_doc = VerificationDocument.objects.filter(user=request.user, doc_type='LICENSE').first()
    
    context = {
        'license_doc': license_doc,
    }
    return render(request, 'core/driver_settings.html', context)

# ==========================================
# REJECT REQUEST (Updated!)
# ==========================================
@login_required
def reject_request(request, request_id):
    # Find the specific job
    assistance_request = get_object_or_404(AssistanceRequest, id=request_id)
    
    # Update the database values so other mechanics can see it
    assistance_request.status = 'Pending'
    assistance_request.mechanic = None
    assistance_request.save()
    
    messages.success(request, "Request rejected. It is now available for other mechanics.")
    
    # Redirect back to the mechanic homepage
    return redirect('mechanic_home')

@login_required
def driver_services_view(request):
    """
    Renders the driver services dashboard where users can select 
    specific roadside assistance services.
    """
    return render(request, 'core/driver_services.html')

@login_required
def driver_requests_view(request):
    """
    Renders all requests initiated by the currently logged-in driver.
    Isolates active requests from historically completed/cancelled ones.
    """
    # 1. Fetch any ongoing request (Pending lookup or actively Accepted/In-Progress)
    active_request = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Pending', 'Accepted', 'In Progress']
    ).first()
    
    # 2. Fetch all historical finalized records (Newest records show first)
    past_requests = AssistanceRequest.objects.filter(
        driver=request.user, 
        status__in=['Completed', 'Cancelled']
    ).order_by('-created_at')
    
    # 3. Compile statistics
    total_count = AssistanceRequest.objects.filter(driver=request.user).count()

    context = {
        'active_request': active_request,
        'past_requests': past_requests,
        'total_count': total_count,
    }
    return render(request, 'core/driver_requests.html', context)

@login_required
def driver_vehicles_view(request):
    """
    Renders the garage view where drivers can see their registered vehicles.
    """
    # Fetch vehicles belonging to the logged-in user. 
    # Change 'owner' to 'user' or 'driver' depending on your models.py setup.
    vehicles = Vehicle.objects.filter(driver=request.user).order_by('-id')
    
    context = {
        'vehicles': vehicles,
    }
    return render(request, 'core/driver_vehicles.html', context)

@login_required
def driver_settings_view(request):
    """
    Renders the settings and profile management panel for the driver application.
    """
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
        # 1. Grab the actual files matching the 'name' attributes in your HTML form
        front_file = request.FILES.get('license_front')
        back_file = request.FILES.get('license_back')

        # 2. Check if at least the front file was uploaded
        if front_file:
            # 3. Save to the VerificationDocument model
            # update_or_create ensures that if they upload again, it overwrites their old submission
            VerificationDocument.objects.update_or_create(
                user=request.user,
                doc_type='LICENSE',  # Automatically tagging it as a license
                defaults={
                    'document_image': front_file,           # Front image
                    'document_image_back': back_file,       # Back image (can be None)
                    'is_approved': False                    # Reset approval status
                }
            )
            
            # 4. Success message and redirect back to settings/profile
            messages.success(request, "License uploaded successfully! It is now pending review.")
            return redirect('driver_settings') 
            
        else:
            # Error if they clicked submit without adding the front photo
            messages.error(request, "Please upload at least the front of your license.")

    # Show the HTML page for a standard GET request
    return render(request, 'core/driver_license.html')