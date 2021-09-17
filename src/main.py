from __future__ import print_function
import datetime
import os.path
import requests 
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_PATH = ".env/client_secret.json"
USER_ACCESS_TOKEN = ".env/token.json"

PONT_CALENDAR_ID = "l0a0e0fpad2g935k1dco82a1u4@group.calendar.google.com"


def quickstart():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(USER_ACCESS_TOKEN):
        creds = Credentials.from_authorized_user_file(USER_ACCESS_TOKEN, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(USER_ACCESS_TOKEN, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId=PONT_CALENDAR_ID, timeMin=now,
                                        maxResults=10, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


def process_records(response):
    bateau_entree = set()
    for record in response["records"]:
        date_start = date_end = record["fields"]["date_passage"]
        type_de_fermeture = record["fields"]["type_de_fermeture"]
        motif = record["fields"]["bateau"]
        start = record["fields"]["fermeture_a_la_circulation"]
        end = record["fields"]["re_ouverture_a_la_circulation"]

        if start[:2] > end[:2]:
            date_end = date_start[:-2] + str(int(date_start[-2:])+1)
        
        if motif != "MAINTENANCE":
            bateaux = motif.split(" / ")
            motif = []
            for bateau in bateaux:
                if bateau != "MAINTENANCE":
                    if bateau not in bateau_entree:
                        bateau_entree.add(bateau)
                        depart_arrivee = "(ARRIVEE)"
                    else:
                        bateau_entree.remove(bateau)
                        depart_arrivee = "(DEPART)"
                    motif.append(f"{bateau} {depart_arrivee}")
            motif = " / ".join(motif)
        
        event = {
            'summary': f"{motif}. Fermeture {type_de_fermeture}",
            'start': {
                'dateTime': f'{date_start}T{start}:00',
                'timeZone': 'Europe/Paris',
            },
            'end': {
                'dateTime': f'{date_end}T{end}:00',
                'timeZone': 'Europe/Paris',
            }
        }
        
        yield event


class MyGoogleCalendarAPI(object):
    
    service = None  # googleAPI service
        
    def __init__(self):
        self.init_service()
        
    def init_service(self):
        creds = None
        if os.path.exists(USER_ACCESS_TOKEN):
            creds = Credentials.from_authorized_user_file(USER_ACCESS_TOKEN, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(USER_ACCESS_TOKEN, 'w') as token:
                token.write(creds.to_json())
        self.service = build('calendar', 'v3', credentials=creds)

    def quick_add_event(self, event_str, calendar_id=PONT_CALENDAR_ID):
        """ 
        """
        return self.service.events().quickAdd(calendarId=calendar_id,
                                            text=event_str).execute()

    def add_event(self, event, calendar_id=PONT_CALENDAR_ID):
        return self.service.events().insert(calendarId=calendar_id, body=event).execute()

    def clear_event(self, calendar_id=PONT_CALENDAR_ID):
        """Can't use this, dont know why"""
        self.service.calendars().clear(calendarId=calendar_id).execute()

    def get_all_events(self, calendar_id=PONT_CALENDAR_ID):
        """"""
        page_token = None
        output = []
        while True:
            events = self.service.events().list(calendarId=calendar_id, pageToken=page_token).execute()
            for event in events['items']:
                output.append(event)
            page_token = events.get('nextPageToken')
            if not page_token:
                break  
        return output

    def delete_event(self, event_id, calendar_id=PONT_CALENDAR_ID):
        """ """
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()




def fetch_data():
    my_api = MyGoogleCalendarAPI()
    API_URL = "https://opendata.bordeaux-metropole.fr/api/records/1.0/search/?dataset=previsions_pont_chaban&rows=1000&facet=bateau"
    r = requests.get(API_URL)
    res = r.json()
    # ### my_api.clear_event(PONT_CALENDAR_ID)
    for event in process_records(res):
        print(f"Calling API INSERT : {event}")
        my_api.add_event(event, PONT_CALENDAR_ID)

def clear_data():
    print("Deleting all events...")
    my_api = MyGoogleCalendarAPI()
    events = my_api.get_all_events()
    for e in events:
        my_api.delete_event(e["id"])

if __name__ == '__main__':
    clear_data()
    fetch_data()
