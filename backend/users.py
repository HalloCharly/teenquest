#Imports
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Tuple
from flask import Flask, session, Request
import passwords
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumber, PhoneNumberFormat
from email_validator import EmailNotValidError, EmailSyntaxError, validate_email 
from flask_login import UserMixin, login_user, current_user
from sqlalchemy.orm import sessionmaker, Session, Query
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
        sessionmaker_jobtaker = sessionmaker(bind=db.engines[global_objects.JOBTAKERS_BINDKEY])
        global sessionmaker_jobmaker
        sessionmaker_jobmaker = sessionmaker(bind=db.engines[global_objects.JOBMAKERS_BINDKEY])
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
        city = db.Column(db.String(40), nullable=False)
        birth_date = db.Column(db.DateTime, default=datetime.min, nullable=False)
        date_time_created = db.Column(db.DateTime, default=datetime.now(timezone.utc).astimezone(), nullable=False)
        rating_avg = db.Column(db.Integer, nullable=True)
        rating_count = db.Column(db.Integer, nullable=True)
        gender = db.Column(db.Enum(Gender), nullable=False)
        pronouns = db.Column(db.String(11), nullable=False)
        job_ammount_done = db.Column(db.Integer, default=0, nullable=False)
        roles = _roles
    
        def __init__(self, first_name, last_name, email, phone_number, country, city, birth_date, gender, pronouns):
            self.first_name = first_name
            self.last_name = last_name
            self.email = email
            self.phone_number = phone_number
            self.country = country
            self.city = city
            self.birth_date = birth_date
            self.gender = gender
            self.pronouns = pronouns

        def __repr__(self) -> str:
            return f"""User{'\n'}{self.id}{'\n'}{self.first_name}{'\n'}{self.last_name}{'\n'}{self.email}{'\n'}{self.phone_number}{'\n'}{self.country}{'\n'}{self.city}{'\n'}
        {self.birth_date}{'\n'}{self.date_time_created}{'\n'}{self.rating_avg}{'\n'}{self.job_ammount_done}{'\n'}{self.gender}{'\n'}{self.pronouns}{'\n'}"""
        
        def change_rating(self, rating : int, db_session : Session | None = None, commit : bool = True) -> bool:
            if self == global_objects.admin:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
            if self.rating_avg == None:
                self.rating_avg = rating
                self.rating_count = 1
            else:
                self.rating_avg = int(((float(self.rating_avg) * self.rating_count) + rating) / (self.rating_count + 1))
                self.rating_count += 1
            if db_was_empty or commit:
                db_session.commit()
            return True
        
        def increment_job_ammount_done(self, db_session : Session | None = None, commit : bool = True) -> bool:
            if self == global_objects.admin:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
            self.job_ammount_done += 1
            if db_was_empty or commit:
                db_session.commit()
            return True
            
        def edit_account(self, request : Request, db_session : Session | None = None, commit : bool = True) -> bool:#request.form should contain account data minus email and an old and new password
            #validates and changes user accesible data by a user request
            if self == global_objects.admin:
                return False
            def handle_error(e):
                print(e)
                return False
            try:
                phone_number = phonenumbers.parse(request.form['phone_num'])
                if(not phonenumbers.is_valid_number(phone_number)):
                    return handle_error("Invalid phone number")
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
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
            user_type = get_user_type(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
            db_session.query(user_type).filter(user_type.id == self.id).update({
                user_type.first_name : request.form['first_name'],
                user_type.last_name : request.form['last_name'],
                user_type.phone_number : phonenumbers.format_number(phone_number, PhoneNumberFormat.E164),
                user_type.country : country,
                user_type.city : request.form['city'],
                user_type.birth_date : birthdate,
                user_type.gender : gender,
                user_type.pronouns : f"{request.form['pronouns_1']}/{request.form['pronouns_2']}"
            })
            #self.first_name = request.form['first_name']
            #self.last_name = request.form['last_name']
            #self.phone_number = phonenumbers.format_number(phone_number, PhoneNumberFormat.E164)
            #self.country = country
            #self.birth_date = birthdate
            #self.gender = gender
            #self.pronouns = f"{request.form['pronouns_1']}/{request.form['pronouns_2']}"
            db_session.flush()
            search = passwords.get_password_by_id(self.id, self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
            if(search == None):
                return False
            (password_session, query) = search
            if not query.first().edit_password(request.form['password'], password_session):
                return False
            password_session.commit()
            if db_was_empty or commit:
                db_session.commit()
            print(self)
            return True
        
        def delete_account(self, db_session : Session | None = None, commit : bool = True) -> bool:
            #deletes a user account and password from the dbs
            if self == global_objects.admin:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
            search = passwords.get_password_by_id(self.id, self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
            if(search == None):
                return False
            (password_session, query) = search
            if not query.first().delete_password(password_session):
                return False
            password_session.commit()
            db_session.delete(self)
            if db_was_empty or commit:
                db_session.commit()
            return True
        
    return DynamicUser

JobTaker = user_model_factory(global_objects.JOBTAKERS_BINDKEY, {global_objects.jobtaker_role})
JobMaker = user_model_factory(global_objects.JOBMAKERS_BINDKEY, {global_objects.jobmaker_role})
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
    
def get_user_by_id(user_id, is_jobtaker) -> Tuple[Session, Query[Any]] | None:
    #gets a user by id
    if(user_id == 0):
        return None
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    user_type = get_user_type(is_jobtaker)
    query = db_session.query(user_type).filter(user_type.id == user_id)
    if(query.count() != 1):
        return None
    return (db_session, query)

def get_user_by_email(email, is_jobtaker) -> Tuple[Session, Query[Any]] | None:
    #gets user by email
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        print(str(e))
        return None
    if email == global_objects.admin.email:
        return global_objects.admin
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    user_type = get_user_type(is_jobtaker)
    query = db_session.query(user_type).filter(user_type.email == email)
    if(query.count() != 1):
        return None
    return (db_session, query)

def get_user_by_phone(phone_number, is_jobtaker) -> Tuple[Session, Query[Any]] | None:
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
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    user_type = get_user_type(is_jobtaker)
    query = db_session.query(user_type).filter(user_type.phone_number == phonenumbers.format_number(phone_number, PhoneNumberFormat.E164))
    if(query.count() != 1):
        return None
    return (db_session, query)

@login_manager.user_loader
def load_user(user_id):
    #gets a user depending on the session account type
    if(session['account_type'] == global_objects.ADMIN_SESSION_NAME):
        return global_objects.admin
    elif(session['account_type'] == global_objects.JOBTAKER_SESSION_NAME or session['account_type'] == global_objects.JOBMAKER_SESSION_NAME):
        db_session = get_user_session(session['account_type'] == global_objects.JOBTAKER_SESSION_NAME)
        db_session.begin()
        return db_session.query(get_user_type(session['account_type'] == global_objects.JOBTAKER_SESSION_NAME)).get({"id":int(user_id)})
    else:
        return None

def validate_user_creation_request(request : Request) -> bool:
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
        date = datetime.strptime(request.form['birthdate'], "%Y-%m-%d").date()
    except ValueError as e:
        return handle_error(e)
    if(date > datetime.now(timezone.utc).astimezone().date()):
        return handle_error("Invalid bdate")
    try:
        Gender(int(request.form['gender']))
    except:
        return handle_error(e)
    return True

def validate_login_attempt(request, is_jobtaker) -> bool:#request.form should contain a password and an email
    #validates and compares a provided email and password /w the dbs
    search = get_user_by_email(request.form['email'], is_jobtaker)
    if(search == None):
        return False
    (_, user_query) = search 
    search = passwords.get_password_by_id(user_query.first().id, is_jobtaker)
    if(search == None):
        return False
    (_, password_query) = search 
    if not password_query.first().check_password_hash(request.form['password']):
        return False
    session['account_type'] = (lambda x : global_objects.JOBTAKER_SESSION_NAME if x else global_objects.JOBMAKER_SESSION_NAME)(is_jobtaker)
    login_user(user_query.first())
    identity_changed.send(app, identity=Identity(user_query.first().id))
    return True

def create_account(request, is_jobtaker) -> bool:#request.form should contain account data and a password
    #validates, creates and adds a user+psswrd to the dbs from a user request
    #acc creation takes a while cuz we need to verify email deliverability
    if not validate_user_creation_request(request):
        return False
    email = validate_email(request.form['email'], check_deliverability=True).normalized
    phone_number = phonenumbers.parse(request.form['phone_num'])
    if get_user_by_email(email, is_jobtaker) != None:
        print("email already in use")
        return False
    if get_user_by_phone(phone_number, is_jobtaker) != None:
        print("phone already in use")
        return False
    user = get_user_type(is_jobtaker)(request.form['first_name'], request.form['last_name'], email, phonenumbers.format_number(phone_number, PhoneNumberFormat.E164), Country(request.form['country']), request.form['city'], datetime.strptime(request.form['birthdate'], "%Y-%m-%d").date(), Gender(int(request.form['gender'])), f"{request.form['pronouns_1']}/{request.form['pronouns_2']}")
    #add password to db
    if user == global_objects.admin:
        return False
    user_session = get_user_session(is_jobtaker)
    user_session.begin()
    if get_user_by_email(user.email, is_jobtaker) != None:
        return False
    if get_user_by_phone(user.phone_number, is_jobtaker) != None:
        return False
    user_session.add(user)
    user_session.flush()
    user_id = user.id
    if not passwords.add_user_password_to_db(user_id, request.form['password'], is_jobtaker):
        return False
    user_session.commit()#we commit it after adding the password, to avoid desync in case of failure to commit password
    session['account_type'] = (lambda x : global_objects.JOBTAKER_SESSION_NAME if x else global_objects.JOBMAKER_SESSION_NAME)(is_jobtaker)
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
    if(global_objects.admin_password.check_password_hash(password)):
        session['account_type'] = global_objects.ADMIN_SESSION_NAME
        login_user(global_objects.admin)
        identity_changed.send(app, identity=Identity(global_objects.admin.id))
        return True
    else:
        return False