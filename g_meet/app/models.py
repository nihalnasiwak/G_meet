from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.conf import settings
class GoogleAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.TextField()
    refresh_token = models.TextField()
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()

    universe_domain = models.CharField(max_length=255, blank=True, null=True)
    account = models.CharField(max_length=255, blank=True, null=True)
    expiry = models.DateTimeField(blank=True, null=True)


class CustomUser(AbstractUser):
    
    is_in_call = models.BooleanField(default=False)
    current_meeting_link = models.URLField(null=True, blank=True)
    current_event_id = models.CharField(max_length=200, null=True, blank=True)
    current_space_id = models.CharField(max_length=200, null=True, blank=True)
    current_space_name = models.CharField(max_length=200, null=True, blank=True)


class Group(models.Model):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    def __str__(self):
        return self.name