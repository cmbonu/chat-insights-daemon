import logging
import jwt
import json
import uuid
import requests
from datetime import datetime, timedelta
from logging import handlers
from functools import wraps
from flask import request, jsonify, session,current_app
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from decimal import Decimal

ARRAYS_IN_DICT = 1
DICTS_IN_ARRAY = 0
JWT_ALGO = 'HS256'
log_format = '%(asctime)s ::: %(levelname)s ::: %(message)s '
date_format = '%d/%m/%Y %I:%M:%S %p'
formatter = logging.Formatter(fmt=log_format,datefmt=date_format)
console_handler=logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

def get_unique_identifier(id_part):
    return f'{uuid.uuid4().hex[:6].upper()}{str(id_part)}'

def setup_logger(module_name, logging_level, console_log):
    """Create 2 Rotating File loggers for ERROR and Other logs levels

    Arguments:
        module_name {str} -- Name of the logger. Ideally should be the name of calling module.
        logging_level {int} -- Default Logging level (logging.DEBUG,logging.INFO.logging.WARNING,logging.ERROR.logging.CRITICAL)
        console_log {int} -- Log to console flag 0 - Do not log to console, Anything else logs to console

    Returns:
        logger -- creates and returns a logger for the calling module
    """
    #Default Handler
    file_handler = handlers.RotatingFileHandler(f'logs/{module_name}.log',maxBytes=5242880,backupCount=20)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging_level)

    #Error Handler
    error_file_handler = handlers.RotatingFileHandler(f'logs/{module_name}_error.log',maxBytes=5242880,backupCount=20)
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    if console_log:
        logger.addHandler(console_handler)

    return logger

def log_error(module_name,function_name, error_detail):
    module_logger = logging.getLogger(module_name)
    module_logger.error(f'Exception in {module_name}.{function_name} - {error_detail}')

def basic_logger(f):
    """Logging decorator

    Arguments:
        f {function} -- Function to be decorated with logging

    Returns:
        function -- decorated function
    """
    @wraps(f)
    def log_function_call(*args,**kwargs):
        f_name = f.__name__
        f_module = f.__module__
        f_module_logger = logging.getLogger(f_module)
        f_module_logger.info(f'Call {f_module}.{f_name}')
        #f_response = f(*args,**kwargs)
        return f(*args,**kwargs)

    return log_function_call

def process_results(results, output_type = DICTS_IN_ARRAY, stringify_date=False):
    """Packages SQLAlchemy resultset into a array/ dictionaries

    Arguments:
        results [resultset] -- SQLAlchemy resultset
        output_type [int] -- Preferred output format

    Returns:
        [array] -- [array of dictionaries version of the result set]
    """
    if not results:
        return None

    def convert_value(column_value, stringify_date):
        if isinstance(column_value, Decimal):
            return float(column_value)
        if isinstance(column_value, datetime) and stringify_date:
            return column_value.strftime('%Y-%m-%d')
        return column_value

    #data_array = None
    if output_type == DICTS_IN_ARRAY:
        data_array = [ {col:convert_value(row[col],stringify_date) for col in row.keys()} for row in results]

    if output_type == ARRAYS_IN_DICT:
        data_array = {}
        for position, row in enumerate(results):
            for col in row.keys():
                if not position:
                    data_array[col] = []
                col_value = convert_value(row[col],stringify_date)
                data_array[col].append(col_value)
    return data_array

def validate_session(f):
    """Session validation decorator

    Arguments:
        f [function] -- Decorated function

    Returns:
        [decorator] -- Decorator
    """
    @wraps(f)
    def decorator(*args, **kwargs):

        if 'user_id' in session:
            user_id = session['user_id']
            ##Validate ID
            if user_id == request.form['user_id']:
                return f(*args,**kwargs)
            else:
                return jsonify({'message': 'Invalid Session'}),401
        else:
            return jsonify({'message': 'Invalid Session'}),401
    return decorator

def create_token(user_id, session_length, secret_key):
    """[summary]

    Arguments:
        user_id {[type]} -- [description]
        session_length {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    expiry_date = datetime.utcnow()+timedelta(minutes = session_length)
    payload = {'user_id':user_id, 'exp':expiry_date}
    return jwt.encode(payload,secret_key,JWT_ALGO).decode('UTF-8')

def get_userid_from_jwttoken(request):
    """Extract user_id field from JWT Token

    Args:
        request (HTTP request): Flask HTTP request object

    Returns:
        [int]: User Identifier
    """
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header[0:7] == 'Bearer':
            token = auth_header[7:]
        else:
            token = auth_header
    if not token:
        return token

    try:
        token_data = jwt.decode(token, current_app.config['SECRET_KEY'])
        return token_data['user_id']
    except:
        return None

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return jsonify({'message': 'a valid token is missing'}),400

        try:
            token_data = jwt.decode(token, current_app.config['SECRET_KEY'])
        except:
            return jsonify({'message': 'token is invalid'}),400

        return f(*args, **kwargs)
    return decorator

def auth_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header[0:7] == 'Bearer':
                token = auth_header[7:]
            else:
                token = auth_header
        if not token:
            return jsonify({'message': 'Missing Token'}),400

        try:
            token_data = jwt.decode(token, current_app.config['SECRET_KEY'])
            #TODO : Verify JWT user is the same as request user
            #request_data = json.loads(request.get_json())
        except:
            return jsonify({'message': 'Invalid Token'}),400
        return f(*args, **kwargs)

    return decorator

def send_email_with_sendgrid_template(api_token,from_email,to_email,template_id,template_data_dict):
    
    message = Mail(
        from_email=from_email,
        to_emails=to_email)
    message.dynamic_template_data = template_data_dict
    message.template_id = template_id
    try:
        sg = SendGridAPIClient(api_token)
        response = sg.send(message)
        #print(response.status_code)
        #print(response.body)
        #print(response.headers)
    except Exception as e:
        print(e.message)

def send_email_with_sendinblue_template(api_token,to_email,from_email,template_id,template_data_dict):
    url = "https://api.sendinblue.com/v3/smtp/email"
    payload = {"to":[{"email":to_email}],"replyTo":{"email":from_email},"templateId":template_id,"params":template_data_dict}
    
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'api-key': api_token
        }
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    print(response.text)

def send_email(api_token,from_email,to_email,template_id,**template_data):
    #send_email_with_sendgrid_template(api_token,from_email,to_email,template_id,template_data)
    send_email_with_sendinblue_template(api_token,to_email,from_email,template_id,template_data)
#send_email_template()