
### WhatsApp Chat Analytics Back End
Backend service for processing WhatsApp chat export files for analysis

Components
- Chat engine daemon to process and persist chat text file.
    - Reads from PubSub topic, reads file from GCS, processes and saves to Cloud SQL

### Dependencies
-  Running Postgres Database
-  appconfig.py configuration

### Starting the Service (Development Server)
-  Navigate to the daemon folder `cd daemon`
-  Start the Chat Processor `python chat_processor.py`
