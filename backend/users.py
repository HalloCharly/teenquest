#Imports
from datetime import datetime, timezone
from enum import Enum
from typing import Tuple
from flask import Flask, session
import passwords
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumber, PhoneNumberFormat
from email_validator import EmailNotValidError, EmailSyntaxError, validate_email 
from flask_login import UserMixin, login_user, current_user
from sqlalchemy.orm import sessionmaker, Session
import global_objects
from global_objects import db, login_manager, Gender
from sqlalchemy_utils import EmailType, CountryType, PhoneNumberType, Country
from flask_principal import identity_changed, UserNeed, Identity

#handles user validation, and user db operations(add, edit, delete)

app : Flask

def init_module(application):
    #initializes the users module
    with application.app_context():
        global app
        app = application
        global sessionmaker_jobtaker
        sessionmaker_jobtaker = sessionmaker(bind=db.engines['jobtakers'])
        global sessionmaker_jobmaker
        sessionmaker_jobmaker = sessionmaker(bind=db.engines['jobmakers'])
        global_objects.make_admin_object(Admin)
        global_objects.jobtaker_type = JobTaker
        global_objects.jobmaker_type = JobMaker

def user_model_factory(bind_key, _roles):
    #creates a user class/db model
    class DynamicUser(db.Model, UserMixin):
        __bind_key__ = bind_key
        __tablename__ = bind_key
        id = db.Column(db.Integer, primary_key=True, unique=True)
        first_name = db.Column(db.String(30), nullable=False)
        last_name = db.Column(db.String(30), nullable=False)
        email = db.Column(EmailType, nullable=False, unique=True)
        phone_number = db.Column(PhoneNumberType, nullable=False, unique=True)
        country = db.Column(CountryType, nullable=False)
        birth_date = db.Column(db.DateTime, default=datetime.min, nullable=False)
        date_time_created = db.Column(db.DateTime, default=datetime.now(timezone.utc).astimezone(), nullable=False)
        rating = db.Column(db.Integer, nullable=True)
        gender = db.Column(db.Enum(Gender), nullable=False)
        pronouns = db.Column(db.String(11), nullable=False)
        job_ammount_started = db.Column(db.Integer, default=0, nullable=False)
        job_ammount_finished = db.Column(db.Integer, default=0, nullable=False)
        roles = _roles
    
        def __init__(self, first_name, last_name, email, phone_number, country, birth_date, gender, pronouns):
            self.first_name = first_name
            self.last_name = last_name
            self.email = email
            self.phone_number = phone_number
            self.country = country
            self.birth_date = birth_date
            self.gender = gender
            self.pronouns = pronouns

        def __repr__(self) -> str:
            return f"""User{'\n'}{self.id}{'\n'}{self.first_name}{'\n'}{self.last_name}{'\n'}{self.email}{'\n'}{self.phone_number}{'\n'}{self.country}{'\n'}
        {self.birth_date}{'\n'}{self.date_time_created}{'\n'}{self.rating}{'\n'}{self.job_ammount_started}{'\n'}{self.job_ammount_finished}{'\n'}{self.gender}{'\n'}{self.pronouns}{'\n'}"""
        
    return DynamicUser

JobTaker = user_model_factory("jobtakers", {global_objects.jobtaker_role})
JobMaker = user_model_factory("jobmakers", {global_objects.jobmaker_role})
Admin = user_model_factory("", {global_objects.jobtaker_role, global_objects.jobmaker_role, global_objects.admin_role})

def get_user_type(is_jobtaker):
    #returns the user type for jobtakers or jobmakers
    if is_jobtaker:
        return JobTaker
    else:
        return JobMaker
    
def get_user_session(is_jobtaker) -> Session:
    #returns a db session for jobtakers or jobmakers
    if is_jobtaker:
        return sessionmaker_jobtaker()
    else:
        return sessionmaker_jobmaker()
    
def get_user_by_id(user_id, is_jobtaker):
    #gets a user by id
    if(user_id == 0):
        return global_objects.admin
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    user_type = get_user_type(is_jobtaker)
    query = db_session.query(user_type).filter(user_type.id == user_id)
    if(query.count() != 1):
        return None
    return query.first()

def get_user_by_email(email, is_jobtaker):
    #gets user by email
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        print(str(e))
        return None
    if email == global_objects.admin.email:
        return global_objects.admin
    else:
        db_session = get_user_session(is_jobtaker)
        db_session.begin()
        user_type = get_user_type(is_jobtaker)
        query = db_session.query(user_type).filter(user_type.email == email)
        if(query.count() != 1):
            return None
        return query.first()

def get_user_by_phone(phone_number, is_jobtaker):
    #gets user by phone number
    if(not isinstance(phone_number, PhoneNumber)):
        phone_number = phonenumbers.parse(phone_number)
    try:
        if(not phonenumbers.is_valid_number(phone_number)):
            return None
    except NumberParseException as e:
        print(str(e))
        return None
    if phonenumbers.format_number(phone_number, PhoneNumberFormat.E164) == global_objects.admin.email:
        return global_objects.admin
    else:
        db_session = get_user_session(is_jobtaker)
        db_session.begin()
        user_type = get_user_type(is_jobtaker)
        query = db_session.query(user_type).filter(user_type.phone_number == phonenumbers.format_number(phone_number, PhoneNumberFormat.E164))
        if(query.count() != 1):
            return None
        return query.first()

@login_manager.user_loader
def load_user(user_id):
    #gets a user depending on the session account type
    if(session['account_type'] == "admin"):
        return global_objects.admin
    elif(session['account_type'] == "jobtaker" or session['account_type'] == "jobmaker"):
        db_session = get_user_session(session['account_type'] == "jobtaker")
        db_session.begin()
        return db_session.query(get_user_type(session['account_type'] == "jobtaker")).get({"id":int(user_id)})
    else:
        return None

def add_user_to_db(user, is_jobtaker, force_add=False) -> Tuple[bool, int | None, Session]:
    #add user to the db (doesn't commit it!!!!!!)
    if user == global_objects.admin:
        return (False, None, None)
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    if get_user_by_email(user.email, is_jobtaker) != None and not force_add:
        return (False, None, None)
    if get_user_by_phone(user.phone_number, is_jobtaker) != None and not force_add:
        return (False, None, None)
    db_session.add(user)
    db_session.flush()
    user_id = user.id
    return (True, user_id, db_session)

def validate_user_creation_request(request) -> bool:
    #checks if request.form contains parsable information
    def handle_error(e):
        print(e)
        return False
    try:
        email = validate_email(request.form['email'], check_deliverability=True).normalized
        if(email == global_objects.admin.email):
            return handle_error("admin")
    except EmailSyntaxError as e:
        return handle_error(e)
    except Exception as e:
        return handle_error(e)
    try:
        phone_number = phonenumbers.parse(request.form['phone_num'])
        if(not phonenumbers.is_valid_number(phone_number)):
            return handle_error("invalid")
        if(phonenumbers.format_number(phone_number, PhoneNumberFormat.E164) == global_objects.admin.phone_number):
            return handle_error("admin")
    except NumberParseException as e:
        return handle_error(e)
    try:
        Country(request.form['country'])
    except ValueError as e:
        return handle_error(e)
    try:
        datetime.strptime(request.form['birthdate'], "%Y-%m-%d").date()
    except ValueError as e:
        return handle_error(e)
    try:
        Gender(int(request.form['gender']))
    except:
        return handle_error(e)
    return True

def validate_login_attempt(request, is_jobtaker) -> bool:#request.form should contain a password and an email
    #validates and compares a provided email and password /w the dbs
    user = get_user_by_email(request.form['email'], is_jobtaker)
    if(user == None):
        return False
    if not passwords.check_password_hash(user, request.form['password'], is_jobtaker):
        return False
    session['account_type'] = (lambda x : "jobtaker" if x else "jobmaker")(is_jobtaker)
    login_user(user)
    print("que")
    identity_changed.send(app, identity=Identity(user.id))
    return True

def edit_account(user, request, is_jobtaker) -> Tuple[bool, int | None]:#request.form should contain (account data-email) and an old and new password
    #validates and changes user accesible data by a user request
    if user == global_objects.admin:
        return (False, None)
    if(get_user_by_email(user.email, is_jobtaker) == None or user == None):
        print("email is not in use")
        return False
    def handle_error(e):
        print(e)
        return False
    try:
        phone_number = phonenumbers.parse(request.form['phone_num'])
        if(not phonenumbers.is_valid_number(phone_number)):
            return handle_error("griker")
    except NumberParseException as e:
        return handle_error(e)
    try:
        country = Country(request.form['country'])
    except ValueError as e:
        return handle_error(e)
    try:
        birthdate = datetime.strptime(request.form['birthdate'], "%Y-%m-%d").date()
    except ValueError as e:
        return handle_error(e)
    try:
        gender = Gender(int(request.form['gender']))
    except:
        return handle_error(e)
    user_type = get_user_type(is_jobtaker)
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    db_session.query(user_type).filter(user_type.id==user.id).update({
        user_type.first_name: request.form['first_name'],
        user_type.last_name: request.form['last_name'],
        user_type.phone_number: phonenumbers.format_number(phone_number, PhoneNumberFormat.E164),
        user_type.country: country,
        user_type.birth_date: birthdate,
        user_type.gender: gender,
        user_type.pronouns: f"{request.form['pronouns_1']}/{request.form['pronouns_2']}"
    })
    if not passwords.edit_password(user.id, request.form['password'], is_jobtaker):
        return False
    db_session.commit()
    return True

def create_account(request, is_jobtaker) -> bool:#request.form should contain account data and a password
    #validates, creates and adds a user+psswrd to the dbs from a user request
    if not validate_user_creation_request(request, is_jobtaker):
        return False
    email = validate_email(request.form['email'], check_deliverability=True).normalized
    phone_number = phonenumbers.parse(request.form['phone_num'])
    if(get_user_by_email(email, is_jobtaker) != None):
        print("email already in use")
        return False
    if(get_user_by_phone(phone_number, is_jobtaker) != None):
        print("phone already in use")
        return False
    user = get_user_type(is_jobtaker)(request.form['first_name'], request.form['last_name'], email, phonenumbers.format_number(phone_number, PhoneNumberFormat.E164), Country(request.form['country']), datetime.strptime(request.form['birthdate'], "%Y-%m-%d").date(), Gender(int(request.form['gender'])), f"{request.form['pronouns_1']}/{request.form['pronouns_2']}")
    #add password to db
    (code, user_id, user_session) = add_user_to_db(user, is_jobtaker)
    if not code:
        return False
    code = passwords.add_user_password_to_db(user_id, request.form['password'], is_jobtaker)
    if not code:
        return False
    user_session.commit()#we commit it after adding the password, to avoid desync
    session['account_type'] = (lambda x : "jobtaker" if x else "jobmaker")(is_jobtaker)
    return True

def delete_account(user, session_type) -> bool:
    #deletes a user account
    if user == global_objects.admin or session_type == "admin":
        return False
    if session_type != "jobtaker" and session_type != "jobmaker":
        return False
    user_type = get_user_type(session_type == "jobtaker")
    db_session = get_user_session(session_type == "jobtaker")
    db_session.begin()
    query = db_session.query(user_type).filter(user_type.id == user.id).limit(1)
    passwords.delete_password(query.first().id, session_type)
    query.delete()
    db_session.commit()
    return True

def on_identity_loaded(sender, identity):
    #loads roles to user
    identity.user = current_user
    if(hasattr(identity.user, "id")):
        identity.provides.add(UserNeed(identity.user.id))
    if(hasattr(identity.user, "roles")):
        for role in identity.user.roles:
            identity.provides.add(role)
    print(identity.provides)#i leave ts on for debuging, it print all usr roles

def validate_admin_login(password) -> bool:
    #checks admin login from user request
    if(passwords.check_password_hash(global_objects.admin, password, False)):
        session['account_type'] = "admin"
        login_user(global_objects.admin)
        identity_changed.send(app, identity=Identity(global_objects.admin.id))
        return True
    else:
        return False