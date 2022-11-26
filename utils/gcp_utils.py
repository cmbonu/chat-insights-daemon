from google.cloud import storage,pubsub_v1

retry_count = 3
publisher =  None #Global PubSub publisher

def get_gcs_blob(bucket_name, file_path,credential_path):
    #gcs_storage = storage.Client.from_service_account_json(credential_path)
    gcs_storage = storage.Client()
    gcs_bucket = gcs_storage.bucket(bucket_name)
    gcs_blob = gcs_bucket.blob(file_path.lower())
    return gcs_blob

def read_file_from_gcs(bucket_name, file_path,credential_path):
    gcs_blob = get_gcs_blob(bucket_name,file_path,credential_path)
    return gcs_blob.download_as_string()
    
def save_file_to_gcs(bucket_name, file_path,credential_path,upload_bytes):
    gcs_blob = get_gcs_blob(bucket_name,file_path,credential_path)
    gcs_blob.upload_from_string(upload_bytes)

def create_pubsub_message(project_id,topic,message,credential_path,**kwargs):
    #Bind to Global Declaration
    global publisher
    topic_name = f'projects/{project_id}/topics/{topic}'
    try:
        msg_id = publisher.publish(topic_name,data=message.encode('utf-8'),**kwargs)
        print('PubSub Created')
    except:
        print('Creating PubSub')
        publisher = pubsub_v1.PublisherClient.from_service_account_json(credential_path)
        msg_id = publisher.publish(topic_name,data=message.encode('utf-8'),**kwargs)
    return msg_id

def create_pubsub_subscription(project_id,subscription_name,credential_path,callback_function):
    subscriber = pubsub_v1.SubscriberClient.from_service_account_json(credential_path)
    subscription_path = subscriber.subscription_path(project_id,subscription_name)
    streaming_pull_future  = subscriber.subscribe(subscription_path,callback=callback_function)
    with subscriber:
        try:
            streaming_pull_future.result(timeout=20)
        except:
            streaming_pull_future.cancel()
    #return subscriber,streaming_pull_future

def callback(message):
    """Basic PubSub callback processor. Acknowledges the message.

    Arguments:
        message {PubSub Message} -- Message Object from Google PubSub.
    """
    message.ack()