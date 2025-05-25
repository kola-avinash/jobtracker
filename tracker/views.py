from django.shortcuts import redirect, render
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

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
    results = service.users().messages().list(userId='me', q='subject:(applied) OR subject:(application)').execute()
    messages = results.get('messages', [])[:10]

    parsed_emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        parsed = {h['name']: h['value'] for h in headers if h['name'] in ['Subject', 'From', 'Date']}
        parsed_emails.append(parsed)

    return render(request, 'tracker/dashboard.html', {'emails': parsed_emails})
