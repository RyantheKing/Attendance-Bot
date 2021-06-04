import http.client
import json
import datetime
import sheets
import classroom
import mail
import time

sheets.initialize()
classroom.initialize()
BOT_COURSES = classroom.get_courses()

def get_zoom_meeting_info(meeting):
    conn = http.client.HTTPSConnection("api.zoom.us")
    conn.request("GET", "/v2/report/meetings/"+str(meeting['id'])+"/participants?page_size=300", headers=headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def get_search_string():
    tm = time.localtime()
    return 'from='+str(tm.tm_year)+'-'+str(tm.tm_mon)+'-'+str(tm.tm_mday)+'&to='+str(tm.tm_year)+'-'+str(tm.tm_mon)+'-'+str(tm.tm_mday)

conn = http.client.HTTPSConnection("api.zoom.us")
user_id_list = []
headers = {  # IMPORTANT REPLACE UPDATED TOKEN ON THE FOLLOWING LINE (leave the word Bearer with a space there)
    'authorization': "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOm51bGwsImlzcyI6ImRhVXlzMHlkUURlX3o4eGpVQ0xOVmciLCJleHAiOjE2NDEwMjQwMDAsImlhdCI6MTYyMjgxNjQ0OH0.tUm_5kW22iOyvnKzyHlvVr_t63WHZOTxvno8XgoERAg",
    'content-type': "application/json"
}
conn.request("GET", "/v2/users?status=active&page_size=300&page_number=1", headers=headers)
res = conn.getresponse()
data = res.read()
new_data = json.loads(data.decode("utf-8"))
for i in new_data['users']:
    user_id_list.append(i['id'])
# page 2
conn.request("GET", "/v2/users?status=active&page_size=300&page_number=2", headers=headers)
res = conn.getresponse()
data = res.read()
new_data = json.loads(data.decode("utf-8"))
for i in new_data['users']:
    user_id_list.append(i['id'])

SHEET = sheets.getSheet()
WHITELIST = sheets.getSheet2()

for i in user_id_list:
    conn = http.client.HTTPSConnection("api.zoom.us")   # edit the stuff below this message for correct date.
    conn.request("GET", "/v2/report/users/"+i+"/meetings?"+get_search_string()+"&page_size=300", headers=headers)
    res = conn.getresponse()
    data = res.read()
    new_data = json.loads(data.decode("utf-8"))
    for meeting in new_data['meetings']:
        if (time.localtime().tm_hour <= 17 and mail.convert_time(meeting["end_time"])[0]<17) or (time.localtime().tm_hour > 17 and mail.convert_time(meeting["end_time"])[0]>=17):
            period_data = sheets.return_list_from_zoom_id(SHEET, meeting["id"])
            if period_data != None:
                students = classroom.get_students_from_code(BOT_COURSES, period_data[1])
                #if not students:
                    #print(meeting["user_email"], period_data)
            else:
                students = None
            new_data = get_zoom_meeting_info(meeting)
            try:
                participants = new_data['participants']
            except:
                participants = []
                #print("participant error", meeting["user_email"])
            absent = []
            present_zoom = []
            present_classroom = []
            if students:
                for student in students:
                    missing = True
                    has_email = True
                    try:
                        email = student["profile"]["emailAddress"]
                    except: 
                        has_email = False
                       #print("student email error", meeting["user_email"])
                    if has_email:
                        for participant in participants:
                            if participant["user_email"] == email: #set to use name as well
                                missing = False
                                present_zoom.append(participant)
                                present_classroom.append(student)
                                break
                    else:
                        missing = False
                        present_zoom.append(participant)
                        present_classroom.append(student)
                    if missing: absent.append(student)
                mail.email_teacher(present_zoom, present_classroom, absent, classroom.get_teacher_from_code(BOT_COURSES, period_data[1])["profile"]["emailAddress"], meeting, participants, WHITELIST)
                    #print(classroom.get_teacher_from_code(BOT_COURSES, period_data[1])["profile"]["emailAddress"])
list_difference = []
for item in WHITELIST:
    if item[0] not in mail.sent_emails:
        list_difference.append(item)
mail.send('attendancebot@lcusd.net', "Teachers who didn't get reports today", str(list_difference))