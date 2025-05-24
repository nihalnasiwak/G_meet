# import os
# import datetime
# from django.shortcuts import redirect, render
# from django.http import HttpResponse
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials

# # Required Google Calendar scope
# SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# # 🔐 OAuth Flow with Fixed Redirect URI
# def authorize(request):
#     flow = InstalledAppFlow.from_client_secrets_file(
#         'credentials/credentials.json',
#         SCOPES,
#         redirect_uri='http://localhost:9090/'
#     )

#     credentials = flow.run_local_server(port=0)
#     request.session['credentials'] = credentials_to_dict(credentials)
#     return redirect('create_meet')

# # 📅 Google Meet Creation View
# def create_meet(request):
#     if 'credentials' not in request.session:
#         return redirect('authorize')

#     creds = Credentials(**request.session['credentials'])

#     service = build('calendar', 'v3', credentials=creds)

#     now = datetime.datetime.utcnow()
#     event = {
#         'summary': 'Namma Mail Meeting',
#         'description': 'Video call via Google Meet',
#         'start': {
#             'dateTime': (now + datetime.timedelta(minutes=10)).isoformat() + 'Z',
#             'timeZone': 'UTC',
#         },
#         'end': {
#             'dateTime': (now + datetime.timedelta(minutes=40)).isoformat() + 'Z',
#             'timeZone': 'UTC',
#         },
#         'conferenceData': {
#             'createRequest': {
#                 'requestId': 'sample123',  # Must be unique for each request
#                 'conferenceSolutionKey': {'type': 'hangoutsMeet'},
#             }
#         },
#         'attendees': [
#             {'email': 'attendee1@example.com'},
#             {'email': 'attendee2@example.com'},
#         ],
#     }

#     created_event = service.events().insert(
#         calendarId='primary',
#         body=event,
#         conferenceDataVersion=1
#     ).execute()

#     meet_link = created_event.get('hangoutLink')
#     return render(request, 'success.html', {'meet_link': meet_link})

# # 🎯 Converts OAuth2 credentials to dict for session storage
# def credentials_to_dict(creds):
#     return {
#         'token': creds.token,
#         'refresh_token': creds.refresh_token,
#         'token_uri': creds.token_uri,
#         'client_id': creds.client_id,
#         'client_secret': creds.client_secret,
#         'scopes': creds.scopes
#     }

from django.contrib.auth import authenticate as auth_user, login, logout

from django.contrib.auth import get_user_model
User = get_user_model()
import os
import uuid
import datetime
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from .models import GoogleAccount , Group
from google.auth.transport.requests import Request
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.utils.http import urlencode
from django.http import JsonResponse

def base(request):
    users = User.objects.filter(is_superuser=False).exclude(email=request.user.email)
    group_list = Group.objects.filter(members=request.user.id)
    print(group_list)
    return render(request, 'base.html', {'users': users, 'group_list': group_list})


def chat_with_user(request, user_id):
    if User.objects.filter(id=user_id).exists() :
        other_user = User.objects.get(id=user_id)
    else:
        other_user = None
   
    calling = request.GET.get('calling') == 'true'
    group_list = Group.objects.filter(members=request.user.id)
    users = User.objects.filter(is_superuser=False).exclude(email=request.user.email)
    return render(request, 'chat_page.html', 
                  {'other_user': other_user,
                    'users': users,
                      'calling': calling,
                      "group_list": group_list,
                      })

def group_chat_with_user(request, user_id):
    
    if Group.objects.filter(id=user_id).exists() :
        selected_group = Group.objects.get(id=user_id)
        print(selected_group.name)
    else:
        selected_group = None
    # selected_group = None
    calling = request.GET.get('calling') == 'true'
    group_list = Group.objects.filter(members=request.user.id)
    users = User.objects.filter(is_superuser=False).exclude(email=request.user.email)
    return render(request, 'group_chat_page.html', 
                  {
                    'users': users,
                      'calling': calling,
                      "group_list": group_list,
                      "selected_group": selected_group})

# Required Google Calendar scope
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_user_credentials(user):
    print('get_user_credentials', user)
    try:
        account = GoogleAccount.objects.get(user=user)
    except GoogleAccount.DoesNotExist:
        return None

    creds = Credentials(
        token=account.token,
        refresh_token=account.refresh_token,
        token_uri=account.token_uri,
        client_id=account.client_id,
        client_secret=account.client_secret,
        scopes=account.scopes.split(','),
    )

    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save updated token to DB
        account.token = creds.token
        account.save()

    return creds
# 🔐 OAuth Flow with Fixed Redirect URI
@login_required
def authorize(request):
    creds = get_user_credentials(request.user)
    if creds and not creds.expired:
        # Already authorized, skip OAuth flow
        return redirect('create_meet')
    
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials/credentials.json',
        SCOPES,
        redirect_uri='http://localhost:9090/'  # must match Google Console
    )

    credentials = flow.run_local_server(port=0)

    # Store tokens in database per user
    GoogleAccount.objects.update_or_create(
        user=request.user,
        defaults={
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': ','.join(credentials.scopes),
        }
    )

    return redirect('create_meet')


# 📅 Create Google Meet Link View
@login_required
def create_meet(request):
    if request.method == 'POST':
        if request.POST.get('recipient'):
            print('recipient')
            recipient_id = request.POST.get('recipient')
            recipient = User.objects.get(id=recipient_id)
            recipient_email = [{'email':recipient.email}]
            group_id = None
        if request.POST.get('group_recipient'):
            print('group_recipient')
            recipient = None
            group_id = request.POST.get('group_recipient')
            group = Group.objects.get(id=group_id)
            recipient_id = [member.id for member in group.members.all()]
            email_list = [{'email':member.email} for member in group.members.all()]
            email_list.remove({'email':request.user.email})
            recipient_email = email_list
     
    
    try:
        account = GoogleAccount.objects.get(user=request.user)
    except GoogleAccount.DoesNotExist:
        return redirect('authorize')

    # Load user's saved credentials
    creds = Credentials(
        token=account.token,
        refresh_token=account.refresh_token,
        token_uri=account.token_uri,
        client_id=account.client_id,
        client_secret=account.client_secret,
        scopes=account.scopes.split(','),
    )

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow()
    event = {
        'summary': 'Nasiwak Messenger Meeting',
        'description': 'Video call via Google Meet',
        'start': {
            'dateTime': (now + datetime.timedelta(minutes=1)).isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': (now + datetime.timedelta(minutes=5)).isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),  # Must be unique
                'conferenceSolutionKey': {'type': 'hangoutsMeet'},
            }
        },
        'attendees': recipient_email,
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    meet_link = created_event.get('hangoutLink')
    print('meet_link:', meet_link)
     # Send a WebSocket message to the receiver notifying them about the call
    if group_id:
        print('Calling websocket---------------Group-----------------------', group_id)
    else:
        print('Calling websocket--------------------------------------', recipient.username)
    channel_layer = get_channel_layer()
    if recipient:
        
        async_to_sync(channel_layer.group_send)(
            f'call_{recipient.id}',  # group name = user ID
            {
                'type': 'call_ring',  # this becomes `call_ring()` in consumer
                'message': f"You have an incoming call from {request.user.username}.",
                'meet_link': meet_link,
                'sender_id': request.user.id,
                'receiver_id': recipient.id
            }
        )
        is_group = False
    else:
        for recipient in recipient_id:
            async_to_sync(channel_layer.group_send)(
                f'call_{recipient}',  # group name = group ID
                {
                    'type': 'call_ring',  # this becomes `call_ring()` in consumer
                    'message': f"You have an incoming call from {request.user.username}.",
                    'meet_link': meet_link,
                    'sender_id': request.user.id,
                    'receiver_id': recipient
                }
            )
            
        is_group = True
        recipient = None
         
    
    async_to_sync(channel_layer.group_send)(
    f'call_{request.user.id}',
    {
        'type': 'call_initiated',
        'sender_id': request.user.id,
        
        'meet_link': meet_link,
        'is_group': is_group
    }
    )

    query_string = urlencode({'calling': 'true'})
    if recipient:
        print('Calling websocket--------------------------------------', recipient.username)
        # url = f"{reverse('chat_with_user', kwargs={'user_id': recipient.id})}?{query_string}"
        url = reverse('chat_with_user', kwargs={'user_id': recipient.id})
    else:
        print('Calling websocket---------------Group-----------------------', group_id)
        url = f"{reverse('group_chat_with_user', kwargs={'user_id': group_id})}?{query_string}"

    return redirect(url)


def create_group(request):
    group_list = Group.objects.filter(members=request.user.id) 
    print(group_list)
    email_list = [{'email':member.email} for member in group_list[0].members.all()]
    print('Email list',email_list)
    email_list.remove({'email':request.user.email})
    print('Email list',email_list)
    users = User.objects.filter(is_superuser=False).exclude(email=request.user.email)
    if request.method == 'POST':
        print('Creating group...',request.POST)
        group_name = request.POST.get('group_name')
        group_users = request.POST.getlist('members')
       
        group = Group.objects.create(name=group_name)
        for user_id in group_users:
            user = User.objects.get(id=user_id)
            group.members.add(user)
        
        group.members.add(request.user)
        group.save()
        return redirect('create_group')
    return render(request, 'create_group.html',
                  {'users': users, 'group_list': group_list})

# from django.shortcuts import redirect
# from django.contrib.auth.decorators import login_required

# from django.urls import reverse
# from urllib.parse import urlencode

# from google.oauth2.credentials import Credentials
# from google.auth.transport.requests import Request
# from google.apps import meet_v2

# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# import datetime
# import uuid

# from google_auth_oauthlib.flow import InstalledAppFlow
# from .models import GoogleAccount
# from .models import GoogleAccount  # Assuming your model name
# import os
# from dateutil.parser import parse as parse_datetime
# from django.utils import timezone
# from django.http import JsonResponse

# def get_user_credentials(user):
#     print('🔐 get_user_credentials →', user)

#     try:
#         account = GoogleAccount.objects.get(user=user)
#     except GoogleAccount.DoesNotExist:
#         return None
    
#      # 🛠️ Fix expiry BEFORE passing to Credentials
#     expiry = account.expiry
#     if expiry and timezone.is_naive(expiry):
#         expiry = timezone.make_aware(expiry, timezone.utc)

#     print(f"[🕒 Expiry] aware={timezone.is_aware(expiry)}, value={expiry}")

#     creds = Credentials(
#         token=account.token,
#         refresh_token=account.refresh_token,
#         token_uri=account.token_uri,
#         client_id=account.client_id,
#         client_secret=account.client_secret,
#         scopes=account.scopes.split(','),
#         # expiry=account.expiry
#     )
    
#     # 🔄 Refresh if expired
#     if creds.expired and creds.refresh_token:
#         creds.refresh(Request())

#         # ✅ Save updated token + expiry
#         account.token = creds.token
#         # account.expiry = creds.expiry
#         # account.save(update_fields=['token', 'expiry'])
#         account.save(update_fields=['token'])

#     return creds





# # SCOPES = ['https://www.googleapis.com/auth/meetings.space.created']

# SCOPES = [
#     "https://www.googleapis.com/auth/meetings.space.created",
#     "https://www.googleapis.com/auth/meetings.space.readonly",
#     # "https://www.googleapis.com/auth/meetings.participant.readonly"
# ]


# @login_required
# def authorize(request):
#     creds = get_user_credentials(request.user)
#     if creds and not creds.expired:
#         return redirect('create_meet')

#     flow = InstalledAppFlow.from_client_secrets_file(
#         'credentials/credentials.json',
#         SCOPES,
#         redirect_uri='http://localhost:9090/'  # must match Google Console
#     )

#     credentials = flow.run_local_server(port=0)

#     # Store credentials in the DB
#     GoogleAccount.objects.update_or_create(
#         user=request.user,
#         defaults={
#             'token': credentials.token,
#             'refresh_token': credentials.refresh_token,
#             'token_uri': credentials.token_uri,
#             'client_id': credentials.client_id,
#             'client_secret': credentials.client_secret,
#             'scopes': ','.join(credentials.scopes),
#             'universe_domain': getattr(credentials, 'universe_domain', ''),
#             'account': getattr(credentials, 'account', ''),
#             # 'expiry': credentials.expiry,
#         }
#     )

#     return redirect('create_meet')







# @login_required
# def create_meet(request):
#     user = User.objects.get(id=request.user.id)
#     if request.method == 'POST':
#         recipient_id = request.POST.get('recipient')
#         recipient = User.objects.get(id=recipient_id)
#         recipient_email = recipient.email

#     try:
#         account = GoogleAccount.objects.get(user=request.user)
#     except GoogleAccount.DoesNotExist:
#         return redirect('authorize')

#     # 🔐 Load credentials
#     creds = Credentials(
#         token=account.token,
#         refresh_token=account.refresh_token,
#         token_uri=account.token_uri,
#         client_id=account.client_id,
#         client_secret=account.client_secret,
#         scopes=['https://www.googleapis.com/auth/meetings.space.created'],
#     )

#     # 🔁 Refresh if needed
#     if not creds.valid and creds.refresh_token:
#         creds.refresh(Request())

#     # 🧠 Initialize Meet API client
#     try:
#         client = meet_v2.SpacesServiceClient(credentials=creds)

#         # 🛠️ Create a new Meet Space (meeting)
#         request_obj = meet_v2.CreateSpaceRequest()
#         response = client.create_space(request=request_obj)
#         response.spaces.member
#         # Full resource name
#         space_name = response.name  # "spaces/abc123def456"
#         print("✅ Full space name:", space_name)
#         user.current_space_name = space_name
#         # Just the space ID
        
#         space_id = space_name.split("/")[-1]
#         print("🆔 Extracted space ID:", space_id)
#         user.current_space_id = space_id
#         user.current_meeting_link = response.meeting_uri
#         print(f'Space created: {response.meeting_uri}')
#         meet_link = response.meeting_uri
#         print(f"✅ Meet link created: {meet_link}")
       
#         # Save the updated user
#         user.save()
#     except Exception as e:
#         print(f"❌ Meet API error: {e}")
#         return redirect('authorize')

#     # 🔔 WebSocket notification
#     print('📞 Calling websocket:', recipient.username)
#     conferences = get_meeting_details(creds)
#     print(f"📋 Conferences Meetings: {conferences}")

   
#     # participants = get_participants(creds)
#     # print(f"👥 Participants Info: {participants}")
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         f'call_{recipient.id}',
#         {
#             'type': 'call_ring',
#             'message': f"You have an incoming call from {request.user.username}.",
#             'meet_link': meet_link,
#             'sender_id': request.user.id,
#         }
#     )

#     # ↪️ Redirect to chat with ?calling=true
#     query_string = urlencode({'calling': 'true'})
#     url = f"{reverse('chat_with_user', kwargs={'user_id': recipient.id})}?{query_string}"
#     return redirect(url)


# def get_meeting_details(creds):
#     client = meet_v2.ConferenceRecordsServiceClient(credentials=creds)
#     request = meet_v2.ListConferenceRecordsRequest()
#     response = client.list_conference_records(request=request)
#     return list(response)

# def list_participants(creds, conference_id):
#     # Create a sync client
#     client = meet_v2.ConferenceRecordsServiceClient(credentials=creds)

#     # Define the parent resource
#     parent = f"conferenceRecords/{conference_id}"

#     # Create request
#     request = meet_v2.ListParticipantsRequest(parent=parent)

#     # Make the request
#     response = client.list_participants(request=request)

#     print(f"👥 Participants in conference {conference_id}:")
#     for participant in response:
#         print("🧑 User ID:", participant.user_id)
#         print("🔖 Display Name:", participant.display_name)
#         print("🕓 Join Time:", participant.join_time)
#         print("🏁 Leave Time:", participant.leave_time)
#         print("―" * 40)

# def get_participant_info(creds, conference_id, participant_id):
#     # Create a sync client
#     client = meet_v2.ConferenceRecordsServiceClient(credentials=creds)

#     # Format the resource name as required
#     name = f"conferenceRecords/{conference_id}/participants/{participant_id}"

#     # Build request
#     request = meet_v2.GetParticipantRequest(name=name)

#     # Call the API
#     response = client.get_participant(request=request)

#     # Print or return the response
#     print("📋 Participant Info")
#     print("👤 User ID:", response.user_id)
#     print("🧑 Name:", response.display_name)
#     print("⏱️ Joined at:", response.join_time)
#     print("🚪 Left at:", response.leave_time)

 
#     return list(response)

@login_required
def mark_joined(request):
    user = request.user
    meet_link = request.GET.get("meet_link")
    event_id = request.GET.get("event_id")

    if meet_link and event_id:
        user.is_in_call = True
        user.current_meeting_link = meet_link
        user.current_event_id = event_id
        user.save()
        return JsonResponse({"status": "joined", "user": user.username})
    else:
        return JsonResponse({"error": "Missing meeting link or event_id"}, status=400)


@login_required
def mark_left(request):
    user = request.user

    user.is_in_call = False
    user.current_meeting_link = None
    user.current_event_id = None
    user.save()
    return JsonResponse({"status": "left", "user": user.username})



# 🏠 Simple Home Page
def home(request):
    users = User.objects.filter(is_superuser=False).exclude(email=request.user.email)
    return render(request, 'home.html', {'users': users})


def signup(request):
    print(User.objects.all())
    if request.method == 'POST':
        print(request.POST)
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        User.objects.create_user(username=username, email=email, password=password)
       
        return redirect('login')
    return render(request, 'signup.html')



def login_user(request):
    if request.method == 'POST':
        print(request.POST) 
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth_user(request, username=username, password=password)
        print(user)
        if user is not None:
            login(request, user)
            return redirect('base')
    return render(request, 'login.html')



def logout_user(request):
    logout(request)
    return redirect('login')
