from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
from datetime import datetime, timezone

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    """Google Calendar APIの認証とサービスの取得を行います。"""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def add_event(summary, description, start_time, end_time, location=None):
    """
    カレンダーにイベントを追加します。
    
    Args:
        summary (str): イベントのタイトル
        description (str): イベントの説明
        start_time (datetime): 開始時刻
        end_time (datetime): 終了時刻
        location (str, optional): 場所
    
    Returns:
        dict: 作成されたイベントの情報
    """
    service = get_google_calendar_service()
    
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
    }
    
    if location:
        event['location'] = location
    
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event

def main():
    # 使用例
    start_time = datetime(2024, 3, 20, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 3, 20, 11, 0, tzinfo=timezone.utc)
    
    event = add_event(
        summary='テストミーティング',
        description='これはテストイベントです。',
        start_time=start_time,
        end_time=end_time,
        location='会議室A'
    )
    print('Event created: %s' % (event.get('htmlLink')))

if __name__ == '__main__':
    main() 