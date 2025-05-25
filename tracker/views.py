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
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Dev only

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
    auth_url, _ = flow.authorization_url(prompt='consent')
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
    service = build('gmail', 'v1', credentials=credentials)

    print("Gmail API connected")

    results = service.users().messages().list(
        userId='me',
        q='application',
        maxResults=20
    ).execute()

    messages = results.get('messages', [])
    print("Fetched Gmail messages:", messages)

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['Subject', 'From', 'Date']
        ).execute()

        headers = msg_data.get('payload', {}).get('headers', [])
        parsed = {h['name']: h['value'] for h in headers if h['name'] in ['Subject', 'From', 'Date']}
        print("Parsed email:", parsed)

        try:
            parsed_date = eutils.parsedate_to_datetime(parsed.get('Date'))
        except Exception as e:
            print("Date parsing failed:", e)
            continue

        if not JobApplication.objects.filter(
            subject=parsed.get('Subject'),
            sender=parsed.get('From'),
            date_received=parsed_date
        ).exists():
            JobApplication.objects.create(
                subject=parsed.get('Subject'),
                sender=parsed.get('From'),
                date_received=parsed_date
            )
            print("Saved to DB:", parsed['Subject'])

    return redirect('dashboard')


def dashboard(request):
    apps = JobApplication.objects.all().order_by('-date_received')
    print("Applications in DB:", apps.count())
    return render(request, 'tracker/dashboard.html', {'applications': apps})


@csrf_exempt
def update_status(request, app_id):
    app = get_object_or_404(JobApplication, id=app_id)
    if request.method == 'POST':
        app.status = request.POST.get('status')
        app.save()
    return redirect('dashboard')


def export_csv(request):
    applications = JobApplication.objects.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="job_applications.csv"'

    writer = csv.writer(response)
    writer.writerow(['Subject', 'From', 'Date', 'Status', 'Notes'])

    for app in applications:
        writer.writerow([app.subject, app.sender, app.date_received, app.status, app.notes])

    return response
