from datetime import datetime
import random
import sys
import time
sys.path.insert(1, '../')
import utils.gcp_utils as gcp_utils
import pandas as pd

_BUCKET_NAME = "chains-tc-in-1"
_MEDIA_KEYWORDS = ['<Media omitted>','image omitted','video omitted','GIF omitted','document omitted']

def has_media(media_string):
    for media_type in _MEDIA_KEYWORDS:
        if media_type in media_string:
            return True
    return False

def chat_unique_count(chat_series):
       return chat_series.nunique()

def is_date(date_string):
    try:
        process_time_field(date_string)
        return True
    except:
        return False

def get_date_and_phone(date_phone_string):
    if ']' in date_phone_string:
        return date_phone_string.split('] ')
    else:
        return date_phone_string.split(' - ') 

def newline_status(chat_line):  
    split_msg = chat_line.split(": ")
    date_and_phone = get_date_and_phone(split_msg[0])
    if len(split_msg) > 1 and len(date_and_phone)>1: ##Default
        return 1, date_and_phone ## Standard
    else: ##Handle Multilines, New Members
        #New Members
        #date_and_phone = split_msg[0].split(' - ')
        if len(date_and_phone) > 1 and is_date(date_and_phone[0]):
            return 2, date_and_phone #New Member
        else:
            return 3, date_and_phone #Message Extension

def process_time_field(time_string):
    if '[' in time_string:
        time_string = time_string[time_string.index('[')+1:]
    try:
        return datetime.strptime(time_string, '%d/%m/%Y, %H:%M')
    except:
        try:
            return datetime.strptime(time_string, '%d/%m/%Y, %H:%M:%S')
        except:
            try:
                return datetime.strptime(time_string, '%m/%d/%y, %I:%M %p')
            except Exception as e:
                raise e

def process_chat_text_export(chat_file):
    '''
    convert export chat text file to a feature array.
    '''
    print('File Length :',len(chat_file))
    msg_vector = []
    new_members = []
    other_events = []
    phone, message, time_of_chat = None,'',None
    for i,chat_line in enumerate(chat_file):
        try:
            line_type, date_and_phone = newline_status(chat_line)
            split_msg = chat_line.split(": ")
            if line_type == 1: #New Message Line
                if phone is not None:
                    msg_vector.append([phone, time_of_chat,message])
                message = ": ".join(split_msg[1:])
                try:
                    #time_of_chat = datetime.strptime(date_and_phone[0].strip(), '%d/%m/%Y, %H:%M')
                    #print(date_and_phone[0])
                    time_of_chat = process_time_field(date_and_phone[0].strip())
                except:
                    message += chat_line
                    continue
                phone = date_and_phone[1]
            elif line_type == 2: #New Member Line
                time_of_chat = process_time_field(date_and_phone[0].strip())
                if (len(date_and_phone) > 1) and ('added' in date_and_phone[1]): 
                    try:
                        admin_phone,new_member_phone = date_and_phone[1].split(' added ')
                        #new_members.append([admin_phone,new_member_phone,time_of_chat,'added'])
                        new_members.append([new_member_phone,time_of_chat,'added'])
                    except:
                        new_member_phone = date_and_phone[1].split(' added ')
                        #new_members.append(['_',new_member_phone,time_of_chat,'added'])
                        new_members.append([new_member_phone,time_of_chat,'added'])
                else:
                    if 'left' in date_and_phone[1]:
                        other_events.append([date_and_phone[1][:-6],time_of_chat,'left'])
                    elif 'security code' in date_and_phone[1]:
                        other_events.append([date_and_phone[1][:-45],time_of_chat,'code'])
                    elif 'icon' in date_and_phone[1]:
                        other_events.append([date_and_phone[1][:-27],time_of_chat,'icon'])
            elif line_type == 3:
                    message += chat_line
        except ValueError as verr:
            print(f'Error Processing Line {i} : ', verr)
        
    return  msg_vector,new_members,other_events

def process_data(file_bytes):
    wcc = file_bytes.decode('utf-8',errors="replace").replace("\x00", "\uFFFD").split('\n') #Take care of the 'NUL' character
    chat_messages,new_members,other_events = process_chat_text_export(wcc)

    #Process Text Data
    for x in chat_messages:
        x.append(len(x[2].split(' '))) #Word Count
        x.append(1 if '://' in x[2] else 0) #Has Link
        x.append(1 if has_media(x[2]) else 0)#Has Media
        x.append(x[1].hour) #Hour
        #x.append(x[1].weekday) #Weekday
        x.append(x[1].month)#Month
        x.append(x[1].year) #Year
        x.append(x[1].replace(hour=0, second=0, minute=0)) #Plain Date

    return chat_messages,new_members,other_events

def data_process_callback(filename):
    # Get the contents of pubsub message and fetch file from gcs
    #bucket_name = "gs://chains-tc-in-1/input/whatsapp-nritech.txt"
    #file_path = "input/whatsapp-nritech.txt"
    file_path = f"input/{filename}"
    out_file_path = f"input/{filename.split('.')[0]}.parquet"

    # Do the heavy lifting and process records
    chat_bytes = gcp_utils.read_file_from_gcs(_BUCKET_NAME, file_path,"config.credential_path")
    chat_messages,new_members,other_events = process_data(chat_bytes)

    chat_msg_columns = ["phone_no","chat_time","chat_message","word_count","has_link","has_media","chat_hour","chat_month","chat_year","ds"]
    chat_msg_df = pd.DataFrame(chat_messages,columns=chat_msg_columns)
    #chat_msg_df.to_csv("chat_messages.csv",index=False)

    gcp_utils.save_file_to_gcs(_BUCKET_NAME, out_file_path,"config.credential_path",chat_msg_df.to_parquet(index=False))
    

#if __name__ == '__main__':
#    data_process_callback()