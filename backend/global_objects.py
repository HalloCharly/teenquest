from datetime import datetime
from enum import Enum
from typing import List
from flask import Flask
from sqlalchemy_utils import Country
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_principal import Principal, Permission, RoleNeed

#holds all the important, project wide variables, enums and types

db = SQLAlchemy()
login_manager = LoginManager()
app : Flask

admin = None
admin_password = None

admin_password_hash = None#todo:move into cfg file or smwhere idk
secret_key = None

JOBTAKERS_BINDKEY : str = "jobtakers"
JOBMAKERS_BINDKEY : str = "jobmakers"

JOBTAKER_PASSWORDS_BINDKEY : str = "jobtaker_passwords"
JOBMAKER_PASSWORDS_BINDKEY : str = "jobmaker_passwords"

JOBS_BINDKEY : str = "jobs"
LOGS_BINDKEY : str = "logs"

DB_BINDKEYS_TO_CREATE : List[str] = [JOBTAKERS_BINDKEY, JOBMAKERS_BINDKEY, JOBTAKER_PASSWORDS_BINDKEY, JOBMAKER_PASSWORDS_BINDKEY, JOBS_BINDKEY, LOGS_BINDKEY]

ANONYMOUS_SESSION_NAME : str = ""
JOBTAKER_SESSION_NAME : str = "jobtaker"
JOBMAKER_SESSION_NAME : str = "jobmaker"
ADMIN_SESSION_NAME : str = "admin"

principals = Principal()
admin_role = RoleNeed('admin')
admin_permission = Permission(admin_role)
jobtaker_role = RoleNeed('jobtaker')
jobtaker_permission = Permission(jobtaker_role)
jobmaker_role = RoleNeed('jobmaker')
jobmaker_permission = Permission(jobmaker_role)

jobtaker_type : type
jobmaker_type : type
jobtaker_password_type : type
jobmaker_password_type : type
job_type : type
log_type : type

CONFIG_ARGS : List[str] = ["-Secret_Key:", "-Admin_Password_Hash:"]

def load_configs():
    #goes thru config_backend.cfg, finds all the args, and reads them (i cooked here)
    global admin_password_hash
    global secret_key
    found_data = {None:None}
    with open('backend_config.cfg', 'r') as file:
        for line in file:
            for key in CONFIG_ARGS:
                line.strip()
                command_index = line.find(key)
                if(command_index == -1):
                    continue
                command_index += len(key)
                start_index = line.find('''"''', command_index, len(line)) + 1
                end_index = line.find('''"''', start_index, len(line))
                found_data[key] = line[start_index:end_index]
        for key, value in found_data.items():
            if key == None:
                continue
            match key:
                case "-Admin_Password_Hash:":
                    admin_password_hash = value
                case "-Secret_Key:":
                    secret_key = value

def init_module(application):
    #sets up the Principals (user session access privileges)
    global app
    app = application
    principals.init_app(application)

class Gender(Enum):
    MALE = 0
    FEMALE = 1
    NONBIN = 2
    OTHER = 3

class JobState(Enum):
    CREATED = 0
    ACCEPTED_TAKER = 1
    ACCEPTED_MAKER = 2
    STARTED = 3
    ENDED = 4
    PAYED = 5

class JobFilter(Enum):
    DEFAULT = 0
    
def make_admin_object(admin_type):
    #creates the admin object
    global admin
    admin = admin_type("admin", "", "", '', Country('BE'), "", datetime.min, Gender.MALE, "que/quem")
    admin.id = 0
    admin.date_time_created = datetime.min
    admin.rating = 0
    admin.job_ammount_started = 0
    admin.job_ammount_finished = 0

def make_admin_password_object(admin_password_type):
    #creates the admin password object
    global admin_password
    admin_password = admin_password_type(0, admin_password_hash, "")


