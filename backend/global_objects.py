from datetime import datetime
from enum import Enum
from typing import List, Tuple
from flask import Flask
from sqlalchemy_utils import Country
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_principal import Principal, Permission, RoleNeed

#holds all the important, project wide variables, enums and types

db = SQLAlchemy()
login_manager = LoginManager()
app : Flask

testing = False #The backend testing var, turn off for prod & frontend tests

admin = None
admin_password = None

admin_password_hash = "c31083adbb87e2490499a657d7f790dbfa7571f5f639b64c1e6ce44d7f06c4d2"

JOBTAKERS_BINDKEY : str = "jobtakers"
JOBMAKERS_BINDKEY : str = "jobmakers"

JOBTAKER_PASSWORDS_BINDKEY : str = "jobtaker_passwords"
JOBMAKER_PASSWORDS_BINDKEY : str = "jobmaker_passwords"

JOBS_BINDKEY : str = "jobs"
LOGS_BINDKEY : str = "logs"

DB_BINDKEYS_TO_CREATE : Tuple[str] = (JOBTAKERS_BINDKEY, JOBMAKERS_BINDKEY, JOBTAKER_PASSWORDS_BINDKEY, JOBMAKER_PASSWORDS_BINDKEY, JOBS_BINDKEY, LOGS_BINDKEY)

ANONYMOUS_SESSION_NAME : str = ""
JOBTAKER_SESSION_NAME : str = "jobtaker"
JOBMAKER_SESSION_NAME : str = "jobmaker"
ADMIN_SESSION_NAME : str = "admin"

USER_CREATION_REQ_FORM_KEYS : Tuple[str] = ('email', 'phone_num', 'country', 'birthdate', 'gender')
USER_EDITING_REQ_FORM_KEYS : Tuple[str] = ('phone_num', 'country', 'birthdate', 'gender')

EMAIL_CONFIRMATION_SALT : str = "confemailnigga"

SEND_EMAIL : bool = True

DB_PATH : str = "postgresql+psycopg://postgres:Kutas001@localhost:5432/"

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