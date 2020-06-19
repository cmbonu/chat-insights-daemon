from datetime import datetime
import random
import sys
import time
sys.path.insert(1, '../')
import appconfig as config
from model.models import *
import utils.basic_utils as basic_utils
import utils.gcp_utils as gcp_utils
from model.db_connector import get_session

def chat_unique_count(chat_series):
       return chat_series.nunique()


def newline_status(chat_line): 
    '''
    Function to process multiline messages.
    '''
    split_msg = chat_line.split(": ")
    date_and_phone = split_msg[0].split(' - ') # date_and_phone = split_msg[0].split(' - +')
    if len(split_msg) > 1 and len(date_and_phone)>1: ##Default
        return 1 ## Standard
    else: ##Handle Multilines, New Members
        #New Members
        date_and_phone = split_msg[0].split(' - +')
        if len(date_and_phone) > 1:
            return 2 #New Member
        else:
            return 3 #Message Extension

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
            line_type = newline_status(chat_line)
            split_msg = chat_line.split(": ")
            date_and_phone = split_msg[0].split(' - ')
            if line_type == 1: #New Message Line
                if phone is not None:
                    msg_vector.append([phone, time_of_chat,message])
                message = ": ".join(split_msg[1:])
                time_of_chat = datetime.strptime(date_and_phone[0].strip(), '%d/%m/%Y, %H:%M')
                phone = date_and_phone[1]
            elif line_type == 2: #New Member Line
                date_and_phone = split_msg[0].split(' - +')
                time_of_chat = datetime.strptime(date_and_phone[0].strip(), '%d/%m/%Y, %H:%M')
                if (len(date_and_phone) > 1) and ('added' in date_and_phone[1]):           
                    admin_phone,new_member_phone = date_and_phone[1].split(' added ')
                    #new_members.append([admin_phone,new_member_phone,time_of_chat,'added'])
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
        x.append(1 if '<Media omitted>' in x[2] else 0)#Has Media
        x.append(x[1].hour) #Hour
        x.append(x[1].weekday) #Weekday
        x.append(x[1].month)#Month
        x.append(x[1].year) #Year
        x.append(x[1].replace(second=0, minute=0)) #Plain Date

    return chat_messages,new_members,other_events
    
def create_header_info_record(
    upload_title ,
    upload_location ,
    upload_date,
    upload_user_id):

    new_chat_upload = ChatUploads(upload_title=upload_title,\
                        upload_location=upload_location,upload_date=upload_date,\
                        upload_user_id=upload_user_id)
    return new_chat_upload

def create_chat_message_record(upload_id,message_array):
    phone = message_array[0]
    time_of_chat = message_array[1]
    message = message_array[2][0:3990]
    word_count = message_array[3]
    has_url = message_array[4]
    has_media = message_array[5]

    new_message = ChatDetail(upload_id=upload_id,member_phone=phone,\
                        chat_time=time_of_chat,chat_message=message,\
                        word_count=word_count,has_url=has_url,has_media=has_media)
    return new_message

def create_other_events_record(upload_id, message_array):
    member_phone = message_array[0]
    event_time = message_array[1],
    event_type = message_array[2]

    new_event = OtherEvents(upload_id=upload_id,member_phone=member_phone,\
                            event_time=event_time,event_type=event_type)
    return new_event


def data_process_callback(pubsub_message):
    # Get the contents of pubsub message and fetch file from gcs
    file_title = pubsub_message.attributes.get('file_title')
    email_address = pubsub_message.attributes.get('email_address')
    bucket_name = pubsub_message.attributes.get('bucket_name')
    file_path = pubsub_message.attributes.get('file_path')
    full_path = pubsub_message.attributes.get('full_path')

    # Acknowledge PubSub
    pubsub_message.ack()

    # Initiate Session
    db_session = get_session()
    # Fetch User
    upload_user_result = db_session.query(User).filter(User.user_email_address == email_address)
    upload_user = upload_user_result[0]

    # Save Chat upload to database
    new_chat_upload = ChatUploads(upload_title=file_title,\
                    upload_location=full_path,upload_date=datetime.now(),\
                    upload_user_id=upload_user.user_id,processed_date=datetime.now())
    db_session.add(new_chat_upload)
    db_session.commit()

    # Do the heavy lifting and process records
    chat_bytes = gcp_utils.read_file_from_gcs(bucket_name, file_path,config.credential_path)
    chat_messages,new_members,other_events = process_data(chat_bytes)
    
    # Save Chat Messages to Database
    chat_db_models = [create_chat_message_record(new_chat_upload.upload_id,x) for x in chat_messages]
    new_user_db_models = [create_other_events_record(new_chat_upload.upload_id,x) for x in new_members]
    other_events_db_models = [create_other_events_record(new_chat_upload.upload_id,x) for x in other_events]

    # Commit Records
    db_session.add_all(chat_db_models)
    db_session.add_all(new_user_db_models)
    db_session.add_all(other_events_db_models)
    db_session.commit()
    db_session.close()

    basic_utils.send_email(config.sendinblue_api_key,config.sendinblue_sender_email,email_address,
                           config.sendinblue_analysis_ready_email_template,analysis_title = file_title )
    
    #TODO Handle Failed Uploads

if __name__ == '__main__':
    while True:
        gcp_utils.create_pubsub_subscription(config.gcp_project_id,config.subscription_name,\
                                             config.credential_path,data_process_callback)
        #print('Waiting...')
        time.sleep(30)