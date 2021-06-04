from __future__ import print_function
import pickle
import os.path
import httplib2
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import mimetypes
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
import base64
import time
import re

sent_emails = []

regex = re.compile('[^a-zA-Z]')

def convert_time(string_time):
    year, string_time = int(string_time[:4]), string_time[5:]
    month, string_time = int(string_time[:2]), string_time[3:]
    day, string_time = int(string_time[:2]), string_time[3:]
    hour, string_time = int(string_time[:2]), string_time[3:]
    minute, string_time = int(string_time[:2]), string_time[3:]
    second = int(string_time[:2])
    if hour < 7: hour = 24 - 7 + hour
    else: hour = hour - 7
    return [hour, minute, second, month, day, year] #[10, 14, 2, 11, 13, 2020] [10, 13, 59, 11, 13, 2020] 2020-11-13T17:14:02Z 2020-11-13T17:13:59Z  

def calculate_difference(end, start):
    difference = [0,0,0,0,0,0]
    if end[2] < start[2]:
        end[1] = end[1] - 1
        difference[2] = 60+end[2]-start[2]
    else: difference[2] = end[2]-start[2]
    if end[1] < start[1]:
        end[0] = end[0] - 1
        difference[1] = 60+end[1]-start[1]
    else: difference[1] = end[1]-start[1]
    if end[0] < start[0]:
        end[3] = end[3] - 1
        difference[0] = 60+end[0]-start[0]
    else: difference[0] = end[0]-start[0]
    if end[3] < start[3]:
        end[4] = end[4] - 1
        difference[3] = 60+end[3]-start[3]
    else: difference[3] = end[3]-start[3]
    if end[4] < start[4]:
        end[5] = end[5] - 1
        difference[4] = 60+end[4]-start[4]
    else: difference[4] = end[4]-start[4]
    difference[5] = end[5]-start[5]
    return difference

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

creds = None

if os.path.exists('token3.pickle'):
    with open('token3.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'mailcredentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token3.pickle', 'wb') as token:
        pickle.dump(creds, token)

def create_message(sender, to, subject, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(msgPlain, 'plain'))
    return {'raw': base64.urlsafe_b64encode(msg.as_string().encode()).decode()}

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        #print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)
        return "Error"
    return "OK"

def send(address, subject, contents):
    service = build('gmail', 'v1', credentials=creds)
    message = create_message('me', address, subject, contents)
    send_message(service, 'me', message)

def email_teacher(present_zoom, present_classroom, absent, address, meeting, participants, WHITELIST):
    start_time = convert_time(meeting["start_time"])
    end_time = convert_time(meeting["end_time"])
    difference = calculate_difference(end_time, start_time)
    subject = 'Attendance Report for '+meeting["topic"] + ' (' + ' '.join(time.ctime().split()[0:3]) + ')'
    contents = 'Meeting Name: '+meeting["topic"]+\
    '\nStart Time: '+str(start_time[0])+':'+str(start_time[1])+\
    '\nEnd Time: '+str(end_time[0])+':'+str(end_time[1])+\
    '\nMeeting Duration: '+str(meeting["duration"])+' minutes'+\
    '\nTotal Participants: '+str(meeting["participants_count"])+'\n'+\
    '(if you wish to stop receiving these reports, please go to this form and edit your response: https://forms.gle/onaRjbQ6FE9ALTaN8)\n'
    no_email_list = []
    no_email_list_raw = []
    absent_raw = []
    for non_raw in absent:
        fullname = non_raw["profile"]["name"]["fullName"].lower().split()
        absent_raw.append(regex.sub('', fullname[0]+fullname[-1])) 
    for participant in participants:
        fullname = (participant['name'].lower().split())
        if (participant['user_email'][-9:] != 'lcusd.net') and (not (True in [regex.sub('', fullname[0]+fullname[-1]) in val for val in no_email_list_raw])):
            no_email_list.append(participant['name'])
            no_email_list_raw.append(regex.sub('', fullname[0]+fullname[-1]))
    if len(no_email_list) > 0:
        contents = contents + '\nATTENTION: These students may appear absent below because they did not use their school email to sign in, please note that they attended: \n'
        contents_temp = contents
        for index in range(len(no_email_list)):
            if not (no_email_list_raw[index] in absent_raw):
                contents = contents + str(no_email_list[index]) + '\n'
        if contents_temp == contents: contents = contents + 'None\n'
    contents = contents + '\nAbsent students:\n'
    contents_temp = contents
    if len(absent_raw) > 0:
        for index in range(len(absent_raw)):
            if not (absent_raw[index] in no_email_list_raw):
                contents = contents + absent[index]["profile"]["name"]["fullName"] + ' (' + absent[index]["profile"]["emailAddress"] + ')' + '\n'
    if contents_temp == contents: contents = contents + 'None\n'
    contents = contents + "\nPresent students:\n"
    index = 0
    for i in present_classroom:
        join_time = convert_time(present_zoom[index]["join_time"])
        leave_time = convert_time(present_zoom[index]["leave_time"])
        duration = calculate_difference(leave_time, join_time)
        try: email = i["profile"]["emailAddress"]
        except: email = 'unknown'
        contents = contents + i["profile"]["name"]["fullName"] + ' (' + email + ')' + '\n'
    classroom_email_list = []
    for i in present_classroom:
        try: classroom_email_list.append(i["profile"]["emailAddress"])
        except: pass
    used_emails = []
    for participant in participants:
        if (participant['user_email'][-9:] == 'lcusd.net') and (participant['user_email'] not in classroom_email_list) and (participant['user_email'] not in used_emails):
            contents = contents + participant['name'] + ' (' + participant['user_email'] + ')' + '\n'
            used_emails.append(participant['user_email'])
    if len(no_email_list) > 0:
        for no_email in no_email_list:
            contents = contents + str(no_email) + '(did not sign in with mylcusd account)' + '\n'
        index+=1
    contents = contents + '\nReport completed: ' + time.ctime()
    contents = contents + '\n\nIMPORTANT: If something looks off or a student was marked wrong, please contact Ryan King at rking21@mylcusd.net so that I can find the problem.'
    #contents = contents + str(participants)
    #contents = contents + '\n'+ '\n'+ str(absent) + '\n'+ str(present_zoom) + '\n'+ str(present_classroom)
    for i in WHITELIST:
        if i[0] == address:
            if i[4] == 'Yes':
                if i[3] == '':
                    #yee
                    # (address, subject)
                    send(address, subject, contents)
                else:
                    send(address, subject, contents) #i[3]
                sent_emails.append(address)