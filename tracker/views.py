from django.shortcuts import redirect, render, get_object_or_404
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime
import email.utils as eutils
from .models import JobApplication
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import csv
from django.db.models import Q
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
SCOPES = [
    'openid',  # ✅ Required to avoid mismatch
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

def home(request):
    return render(request, 'tracker/home.html')

def login(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8000/callback"]
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = 'http://localhost:8000/callback'
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    return redirect(auth_url)

def callback(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8000/callback"]
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = 'http://localhost:8000/callback'
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials

    # Get user profile info
    oauth2_service = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth2_service.userinfo().get().execute()

    user_email = user_info.get('email')
    user_name = user_info.get('name')
    user_picture = user_info.get('picture')

    request.session['user_email'] = user_email
    request.session['user_name'] = user_name
    request.session['user_picture'] = user_picture

    service = build('gmail', 'v1', credentials=credentials)
    results = service.users().messages().list(
        userId='me',
        q='application',
        maxResults=20
    ).execute()

    messages = results.get('messages', [])

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['Subject', 'From', 'Date']
        ).execute()

        headers = msg_data.get('payload', {}).get('headers', [])
        parsed = {h['name']: h['value'] for h in headers if h['name'] in ['Subject', 'From', 'Date']}
        try:
            parsed_date = eutils.parsedate_to_datetime(parsed.get('Date'))
        except Exception:
            continue

        if not JobApplication.objects.filter(
            user_email=user_email,
            subject=parsed.get('Subject'),
            sender=parsed.get('From'),
            date_received=parsed_date
        ).exists():
            JobApplication.objects.create(
                user_email=user_email,
                subject=parsed.get('Subject'),
                sender=parsed.get('From'),
                date_received=parsed_date,
            )

    return redirect('dashboard')

def dashboard(request):
    user_email = request.session.get('user_email')
    user_name = request.session.get('user_name')
    user_picture = request.session.get('user_picture')

    if not user_email:
        return redirect('home')

    status_filter = request.GET.get('status')
    keyword = request.GET.get('q')

    apps = JobApplication.objects.filter(user_email=user_email)

    if status_filter:
        apps = apps.filter(status=status_filter)

    if keyword:
        apps = apps.filter(
            Q(subject__icontains=keyword) |
            Q(sender__icontains=keyword)
        )

    apps = apps.order_by('-date_received')

    return render(request, 'tracker/dashboard.html', {
        'applications': apps,
        'active_status': status_filter,
        'active_keyword': keyword,
        'user_name': user_name,
        'user_email': user_email,
        'user_picture': user_picture,
    })

@csrf_exempt
def update_status(request, app_id):
    app = get_object_or_404(JobApplication, id=app_id)
    if request.method == 'POST':
        app.status = request.POST.get('status')
        app.save()
    return redirect('dashboard')

def export_csv(request):
    user_email = request.session.get('user_email')
    applications = JobApplication.objects.filter(user_email=user_email)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="job_applications.csv"'

    writer = csv.writer(response)
    writer.writerow(['Subject', 'From', 'Date', 'Status', 'Notes'])

    for app in applications:
        writer.writerow([app.subject, app.sender, app.date_received, app.status, app.notes])

    return response

def logout(request):
    request.session.flush()
    return redirect('home')
