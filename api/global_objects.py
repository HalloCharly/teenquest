from datetime import datetime
from enum import Enum
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

def setup_principals(application):
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
    CREATED = 0 #job gets created and put on the market
    ACCEPTED_TAKER = 1
    ACCEPTED_MAKER = 2
    STARTED = 3
    ENDED = 4
    PAYED = 5
    
def make_admin_object(admin_type):
    #creates the admin object
    global admin
    admin = admin_type("admin", "", "", '', Country('BE'), datetime.min, Gender.MALE, "que/quem")
    admin.id = 0
    admin.date_time_created = datetime.min
    admin.rating = 0
    admin.job_ammount_started = 0
    admin.job_ammount_finished = 0


