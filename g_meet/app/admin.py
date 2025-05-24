
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser,GoogleAccount ,Group

@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'refresh_token')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('pk','name')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "username",
        "email",
        "is_staff",
        "is_in_call",
        "current_meeting_link",
        "current_event_id",
    )
    fieldsets = UserAdmin.fieldsets + (
        ("Call Info", {
            "fields": ("is_in_call", "current_meeting_link", "current_event_id")
        }),
    )
