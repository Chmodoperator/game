from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from game.models import Empire, Territory
import random
from django.conf import settings


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Check if user has an empire
            if not hasattr(user, 'empire'):
                return redirect('accounts:create_empire')
            
            return redirect('game:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('accounts:login')


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/register.html')
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Account created successfully! Please create your empire.')
        
        # Auto-login
        login(request, user)
        return redirect('accounts:create_empire')
    
    return render(request, 'accounts/register.html')


@login_required
def profile_view(request):
    """User profile management"""
    if request.method == 'POST':
        # Update profile settings
        profile = request.user.profile
        profile.preferred_theme = request.POST.get('theme', 'green')
        profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.sound_enabled = request.POST.get('sound_enabled') == 'on'
        profile.auto_resource_notifications = request.POST.get('auto_resource_notifications') == 'on'
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
    
    return render(request, 'accounts/profile.html')


@login_required
def create_empire_view(request):
    """Create new empire for user"""
    # Check if user already has an empire
    if hasattr(request.user, 'empire'):
        return redirect('game:dashboard')
    
    if request.method == 'POST':
        empire_name = request.POST['empire_name']
        empire_color = request.POST['empire_color']
        empire_motto = request.POST.get('empire_motto', '')
        
        # Validation
        if Empire.objects.filter(name=empire_name).exists():
            messages.error(request, 'Empire name already exists.')
            return render(request, 'accounts/create_empire.html')
        
        # Create empire and assign starting territory
        with transaction.atomic():
            empire = Empire.objects.create(
                user=request.user,
                name=empire_name,
                color=empire_color,
                motto=empire_motto
            )
            
            # Assign a random starting territory
            assign_starting_territory(empire)
        
        messages.success(request, f'Empire "{empire_name}" created successfully!')
        return redirect('game:dashboard')
    
    # Generate random colors for selection
    colors = ['#00FF00', '#0080FF', '#FF8000', '#FF0080', '#8000FF', '#00FF80']
    
    return render(request, 'accounts/create_empire.html', {'colors': colors})


def assign_starting_territory(empire):
    """Assign a random unoccupied territory to new empire"""
    # Find unoccupied territories
    unoccupied = Territory.objects.filter(owner=None)
    
    if unoccupied.exists():
        # Assign random territory
        territory = random.choice(unoccupied)
        territory.owner = empire
        territory.save()
    else:
        # Create a new territory if all are occupied (shouldn't happen in 50x50 world)
        x = random.randint(0, settings.WORLD_SIZE - 1)
        y = random.randint(0, settings.WORLD_SIZE - 1)
        
        territory, created = Territory.objects.get_or_create(
            x=x, y=y,
            defaults={
                'owner': empire,
                'terrain_type': random.choice(['plains', 'forest', 'desert']),
                'resource_bonus': random.choice(['energy', 'minerals', 'food', 'none'])
            }
        )
        
        if not created and territory.owner is None:
            territory.owner = empire
            territory.save()
