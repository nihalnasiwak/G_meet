"""
URL configuration for g_meet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_user, name='login'),
    path('base/', views.base, name='base'),
    path('signup/', views.signup, name='signup'),
    path('home/', views.home, name='home'),
    path('chat_with_user/<int:user_id>/', views.chat_with_user, name='chat_with_user'),
    path('group_chat_with_user/<int:user_id>/', views.group_chat_with_user, name='group_chat_with_user'),
    path('authorize/', views.authorize, name='authorize'),
    path('create_meet/', views.create_meet, name='create_meet'),
    path('call/mark_joined/', views.mark_joined, name='mark_joined'),
    path('call/mark_left/', views.mark_left, name='mark_left'),
    path('create_group/', views.create_group, name='create_group'),
    # Manual
    
    path('logout/', views.logout_user, name='logout'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
