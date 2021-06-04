from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import mail

# make a function that can be triggered somehow
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1NbZL9AIHhIhPqnHFiGfxQaFPHzIzBn90wc1LK3o_VPU'
SPREADSHEET_ID2 = '1_kbuuRHtJHofPuk3c0wOFv7zPzoCE6P7b4MlVT7habw'
RANGE_NAME = 'ForRyan!B2:F'
RANGE_NAME2 = 'Data!B2:F'
creds = None
service = None

def initialize():
    global creds
    if os.path.exists('token2.pickle'):
        with open('token2.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials2.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token2.pickle', 'wb') as token:
            pickle.dump(creds, token)
    global service
    service = build('sheets', 'v4', credentials=creds)

def getSheet():
    global service
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=RANGE_NAME).execute()
    values = result.get('values', [])
    return values

def getSheet2():
    global service
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID2,
                                range=RANGE_NAME2).execute()
    values = result.get('values', [])
    return values

def return_list_from_zoom_id(sheet, meeting_id):
    for i in sheet:
        if str(i[0]).replace(' ','')==str(meeting_id):
            return i
    return None

def main():
    initialize()
    WHITELIST = getSheet2()
    TEACHER_LIST = getSheet()
    print(WHITELIST)
    file = open("WHITELIST.txt", "r")
    old_whitelist = eval(file.read())
    #print(old_whitelist)
    file.close()
    file = open("WHITELIST.txt", "w")
    file.write(str(WHITELIST))
    file.close()
    for index in WHITELIST:
        if index[0] not in [i[0] for i in old_whitelist]:
            if index[0] in [value[4] for value in TEACHER_LIST]:
                mail.send(index[0], 'You have been added to the attendance report mailing list!', 'Thank you for signing up to receive attendance reports.\nDuring the first week of reports please take attendance yourself as well and report any problems that you notice to Ryan King at rking21@mylcusd.net')
            else:
                mail.send((index[0]+', rking21@mylcusd.net'), 'Please reply with zoom and google classroom information to receive attendance reports.', 'Thank you for signing up to receive attendance reports.\nThe program was unable to automatically identfiy your zoom and google classroom information. I apoligize for this inconvenience.\nPlease hit "reply all" on this email and provide your zoom meeting ID (or zoom meeting link) and google classroom join code for each period that you wish to get attendance reports for.\nI again apoligize for the inconvenience and I will email your classes have been added to the system.')

main()