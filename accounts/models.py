from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile for game-specific data"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Game preferences
    preferred_theme = models.CharField(max_length=20, choices=[
        ('green', 'Matrix Green'),
        ('blue', 'Cyber Blue'),
        ('amber', 'Retro Amber'),
        ('red', 'War Red'),
    ], default='green')
    
    # Statistics
    games_played = models.IntegerField(default=0)
    total_play_time = models.IntegerField(default=0)  # in minutes
    achievements = models.JSONField(default=list)
    
    # Settings
    email_notifications = models.BooleanField(default=True)
    sound_enabled = models.BooleanField(default=True)
    auto_resource_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class LoginHistory(models.Model):
    """Track user login history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
