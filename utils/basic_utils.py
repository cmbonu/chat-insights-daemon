import logging
import jwt
import json
import uuid
from datetime import datetime, timedelta
from logging import handlers
from functools import wraps
from flask import request, jsonify, session,current_app
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

def validate_session(f):
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
            # Verify JWT user is the same as request user
            request_data = json.loads(request.get_json())
            if (token_data['user_id'] == request_data['user_id']):
                return f(*args, **kwargs)
            else:
                return jsonify({'message': 'token is invalid'}),400
        except:
            return jsonify({'message': 'token is invalid'}),400

        #return f(current_user, *args, **kwargs)
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
        print(f'Token : |{token}|')
        if not token:
            return jsonify({'message': 'Missing Token'}),400

        try:
            token_data = jwt.decode(token, current_app.config['SECRET_KEY'])
            return f(*args, **kwargs)
        except:
            return jsonify({'message': 'Invalid Token'}),400

    return decorator

def send_plain_email():
    
    message = Mail(
        from_email='from_email@example.com',
        to_emails='to@example.com',
        subject='Sending with Twilio SendGrid is Fun',
        html_content='<strong>and easy to do anywhere, even with Python</strong>')
    try:
        sg = SendGridAPIClient('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')
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)

def send_email_template():
    
    message = Mail(
        from_email='cmbonu@gmail.com',
        to_emails='mbonu.onwukwe@gmail.com',
        html_content='<strong>and easy to do anywhere, even with Python</strong>')
    message.dynamic_template_data = {
        'custom_url': 'https://www.google.com'
    }
    message.template_id = 'd-3aff396273db44c1a3744db3c4a64517'
    try:
        sg = SendGridAPIClient('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')
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)

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

def send_email(api_token,from_email,to_email,template_id,**template_data):
    send_email_with_sendgrid_template(api_token,from_email,to_email,template_id,template_data)
#send_email_template()