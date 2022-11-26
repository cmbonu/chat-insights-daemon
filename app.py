import os

from flask import Flask
import daemon.chat_processor_engine as cpe
from waitress import serve

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello There!"

@app.route("/health-check")
def health_check():
    return {"Status": "Not Implemented"}

@app.route("/load-chat-data")
def run_data_process():
    cpe.data_process_callback()
    return {"Status": "Success"}

if __name__ == '__main__':
    PROD = 1
    if PROD:
        serve(app, listen='*:5000')
    else:
        app.run(debug = True,host='0.0.0.0')