from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timezone
import os
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                # Delete expired token and re-authenticate
                if os.path.exists('token.json'):
                    os.remove('token.json')
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json file not found. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service

def find_free_slots(service, duration_minutes, time_min, time_max):
    """
    Find free slots in the calendar for the given duration and time range
    
    Args:
        service: Google Calendar service object
        duration_minutes: Required meeting duration in minutes
        time_min: Start time in ISO format
        time_max: End time in ISO format
    
    Returns:
        List of free slots with start and end times
    """
    try:
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": "primary"}]
        }

        print(f"Requesting freebusy with body:")
        print(json.dumps(body, indent=2))

        eventsResult = service.freebusy().query(body=body).execute()
        
        if 'calendars' not in eventsResult or 'primary' not in eventsResult['calendars']:
            print("Warning: No calendar data returned")
            return []
        
        busy_times = eventsResult['calendars']['primary'].get('busy', [])
        print(f"Found {len(busy_times)} busy periods")

        free_slots = []
        
        # Parse time strings to datetime objects
        start_time = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Sort busy times by start time
        busy_times.sort(key=lambda x: x['start'])
        
        last_end = start_time

        for busy in busy_times:
            busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
            busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
            
            # Check if there's a free slot before this busy period
            if (busy_start - last_end).total_seconds() >= duration_minutes * 60:
                free_slots.append({
                    'start': last_end.isoformat(),
                    'end': busy_start.isoformat(),
                    'duration_minutes': int((busy_start - last_end).total_seconds() / 60)
                })
            
            last_end = max(last_end, busy_end)

        # Check if there's a free slot after the last busy period
        if (end_time - last_end).total_seconds() >= duration_minutes * 60:
            free_slots.append({
                'start': last_end.isoformat(),
                'end': end_time.isoformat(),
                'duration_minutes': int((end_time - last_end).total_seconds() / 60)
            })

        print(f"Found {len(free_slots)} free slots")
        for slot in free_slots:
            print(f"  - {slot['start']} to {slot['end']} ({slot['duration_minutes']} minutes)")

        return free_slots

    except Exception as e:
        print(f"Error finding free slots: {e}")
        return []

def create_meeting(service, start, end, summary="Scheduled Meeting", description="", attendees=None):
    """
    Create a meeting in Google Calendar
    
    Args:
        service: Google Calendar service object
        start: Start time in ISO format
        end: End time in ISO format
        summary: Meeting title
        description: Meeting description
        attendees: List of attendee email addresses
    
    Returns:
        Meeting HTML link or None if failed
    """
    try:
        # Ensure times are properly formatted
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC'
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 10},       # 10 minutes before
                ],
            },
        }
        
        # Add attendees if provided
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Add conference/meet link
        event['conferenceData'] = {
            'createRequest': {
                'requestId': f"meeting-{int(datetime.now().timestamp())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
        
        print(f"Creating meeting: {summary}")
        print(f"Time: {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%H:%M')} UTC")
        
        event_result = service.events().insert(
            calendarId='primary', 
            body=event,
            conferenceDataVersion=1  # Required for conference data
        ).execute()
        
        meeting_link = event_result.get('htmlLink')
        meet_link = None
        
        # Extract Google Meet link if available
        if 'conferenceData' in event_result and 'entryPoints' in event_result['conferenceData']:
            for entry in event_result['conferenceData']['entryPoints']:
                if entry['entryPointType'] == 'video':
                    meet_link = entry['uri']
                    break
        
        print(f"Meeting created successfully!")
        print(f"Calendar link: {meeting_link}")
        if meet_link:
            print(f"Google Meet link: {meet_link}")
        
        return {
            'calendar_link': meeting_link,
            'meet_link': meet_link,
            'event_id': event_result.get('id')
        }

    except Exception as e:
        print(f"Error creating meeting: {e}")
        return None