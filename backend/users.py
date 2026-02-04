#Imports
from datetime import datetime, time, timezone, timedelta  
from enum import Enum
from sqlite3 import OperationalError
from threading import Lock
from typing import Any, Dict, List, Tuple
from flask import Flask, render_template, session, Request, url_for
import passwords
import phonenumbers
from sqlalchemy import func, type_coerce
from phonenumbers import NumberParseException, PhoneNumber, PhoneNumberFormat
from email_validator import EmailNotValidError, EmailSyntaxError, validate_email 
from flask_login import UserMixin, login_user, current_user
from flask_mail import Mail, Message
from sqlalchemy.orm import sessionmaker, Session, Query, scoped_session
import global_objects
from global_objects import db, login_manager, Gender
from sqlalchemy_utils import EmailType, CountryType, PhoneNumberType, Country
from flask_principal import identity_changed, UserNeed, Identity, identity_loaded
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

#handles user validation, and user db operations(add, edit, delete)

app : Flask

sessionmaker_jobtaker : sessionmaker
jobtaker_lock = Lock()
sessionmaker_jobtaker : sessionmaker
jobmaker_lock = Lock()

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
        id = db.Column(db.Integer(), primary_key=True, unique=True)
        first_name = db.Column(db.String(30), nullable=False)
        last_name = db.Column(db.String(30), nullable=False)
        email = db.Column(EmailType, nullable=False, unique=True)
        phone_number = db.Column(PhoneNumberType, nullable=False, unique=True)
        country = db.Column(CountryType, nullable=False)
        city = db.Column(db.String(40), nullable=False)
        birth_date = db.Column(db.DateTime(), default=datetime.min, nullable=False)
        time_registered = db.Column(db.DateTime(), default=datetime.now(timezone.utc).astimezone(), nullable=False)
        confirmation_email_id = db.Column(db.Integer(), nullable=True)
        time_confirmed = db.Column(db.DateTime(), nullable=True)
        rating_avg = db.Column(db.Integer(), nullable=True)
        rating_count = db.Column(db.Integer(), nullable=True)
        gender = db.Column(db.Enum(Gender), nullable=False)
        pronouns = db.Column(db.String(11), nullable=False)
        job_ammount_done = db.Column(db.Integer(), default=0, nullable=False)
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
        {self.birth_date}{'\n'}{self.time_registered}{'\n'}{self.confirmation_email_id}{'\n'}tcon {self.time_confirmed}{'\n'}{self.rating_avg}{'\n'}{self.job_ammount_done}{'\n'}{self.gender}{'\n'}{self.pronouns}{'\n'}"""
        
        def confirm_registration(self, db_session : Session | None = None, commit : bool = True) -> bool:
            if self.time_confirmed != None:
                return False
            if self == global_objects.admin:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
                
            self.time_confirmed = datetime.now(timezone.utc).astimezone()
            
            if db_was_empty or commit:
                db_session.commit()
                db_session.close()
            return True
        
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
                db_session.close()
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
                db_session.close()
            return True
            
        def edit_account(self, request : Request, db_session : Session | None = None, commit : bool = True) -> bool:#request.form should contain account data minus email and an old and new password
            #validates and changes user accesible data by a user request
            if self == global_objects.admin:
                return False
            (is_valid, formated_data) = validate_user_request(request, global_objects.USER_EDITING_REQ_FORM_KEYS, False)
            if not is_valid:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_user_session(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
                db_session.begin()
            user_type = get_user_type(self.__bind_key__ == global_objects.JOBTAKERS_BINDKEY)
            db_session.query(user_type).filter(user_type.id == self.id).update({
                user_type.first_name : request.form['first_name'],
                user_type.last_name : request.form['last_name'],
                user_type.phone_number : phonenumbers.format_number(formated_data['phone_num'], PhoneNumberFormat.E164),
                user_type.country : formated_data['country'],
                user_type.city : request.form['city'],
                user_type.birth_date : formated_data['birthdate'],
                user_type.gender : formated_data['gender'],
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
                db_session.close()
                return False
            (password_session, query) = search
            if not query.first().edit_password(request.form['password'], password_session):
                db_session.close()
                return False
            password_session.commit()
            if db_was_empty or commit:
                db_session.commit()
                db_session.close()
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
                db_session.close()
                return False
            (password_session, query) = search
            if not query.first().delete_password(password_session):
                db_session.close()
                return False
            password_session.commit()
            db_session.delete(self)
            if db_was_empty or commit:
                db_session.commit()
                db_session.close()
            return True
        
    return DynamicUser

JobTaker = user_model_factory(global_objects.JOBTAKERS_BINDKEY, {global_objects.jobtaker_role})
JobMaker = user_model_factory(global_objects.JOBMAKERS_BINDKEY, {global_objects.jobmaker_role})
Admin = user_model_factory("", {global_objects.jobtaker_role, global_objects.jobmaker_role, global_objects.admin_role})

def get_user_type(is_jobtaker : bool):
    #returns the user type for jobtakers or jobmakers
    if is_jobtaker:
        return JobTaker
    else:
        return JobMaker
    
def get_user_session(is_jobtaker : bool) -> Session:
    #returns a db session for jobtakers or jobmakers
    if is_jobtaker:
        return sessionmaker_jobtaker()
    else:
        return sessionmaker_jobmaker()
    
def get_session_lock(is_jobtaker : bool) -> Lock:
    #returns a db session lock for jobtakers or jobmakers
    if is_jobtaker:
        return jobtaker_lock()
    else:
        return jobmaker_lock()

def get_user_by_id(user_id : int, is_jobtaker : bool) -> Tuple[Session, Query[Any]] | None:
    #gets a user by id
    if(user_id == 0):
        return None
    db_session = get_user_session(is_jobtaker)
    db_session.begin()
    user_type = get_user_type(is_jobtaker)
    query = db_session.query(user_type).filter(user_type.id == int(user_id))
    if(query.count() != 1):
        return None
    return (db_session, query)

def get_user_by_email(email : str, is_jobtaker : bool) -> Tuple[Session, Query[Any]] | None:
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
    query = db_session.query(user_type).filter(user_type.email == str(email))
    if(query.count() != 1):
        return None
    return (db_session, query)

def get_user_by_phone(phone_number : str | PhoneNumber, is_jobtaker : bool) -> Tuple[Session, Query[Any]] | None:
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
    if(session.get('account_type') == global_objects.ADMIN_SESSION_NAME):
        return global_objects.admin
    elif(session.get('account_type') == global_objects.JOBTAKER_SESSION_NAME or session.get('account_type') == global_objects.JOBMAKER_SESSION_NAME):
        db_session = get_user_session(session.get('account_type') == global_objects.JOBTAKER_SESSION_NAME)
        db_session.begin()
        search = get_user_by_id(user_id, session.get('account_type') == global_objects.JOBTAKER_SESSION_NAME)
        if(search == None):
            return None
        user = search[1].first()
        db_session.close()
        return user
    else:
        return None

def validate_user_request(request : Request, keys : List[str], check_email_deliverability : bool = False) -> Tuple[bool, Dict[str,  Any]]:
    #checks if request.form contains parsable information
    def handle_error(e):
        print(e)
        return (False, None)
    output = {}
    for key in keys:
        if request.form.get(key) == None:
            return (False, None)
        match key:
            case 'email':
                try:
                    output['email'] = validate_email(request.form['email'], check_deliverability=check_email_deliverability).normalized
                    if(output['email'] == global_objects.admin.email):
                        return handle_error("admin")
                except EmailSyntaxError as e:
                    return handle_error(e)
                except Exception as e:
                    return handle_error(e)
            case 'phone_num':
                try:
                    output['phone_num'] = phonenumbers.parse(request.form['phone_num'])
                    if(not phonenumbers.is_valid_number(output['phone_num'])):
                        return handle_error("invalid")
                    if(phonenumbers.format_number(output['phone_num'], PhoneNumberFormat.E164) == global_objects.admin.phone_number):
                        return handle_error("admin")
                except NumberParseException as e:
                    return handle_error(e)
            case 'country':
                try:
                    output['country'] = Country(request.form['country'])
                except ValueError as e:
                    return handle_error(e)
            case 'birthdate':
                try:
                    output['birthdate'] = datetime.strptime(request.form['birthdate'], "%Y-%m-%d").astimezone().date()
                except ValueError as e:
                    return handle_error(e)
                if(output['birthdate'] > datetime.now(timezone.utc).astimezone().date()):
                    return handle_error("Invalid bdate")
            case 'gender':
                try:
                    output['gender'] = Gender(int(request.form['gender']))
                except:
                    return handle_error(e)
    output['city'] = request.form['city']
    return (True, output)

def verify_login_attempt(request : Request, is_jobtaker : bool) -> bool:#request.form should contain a password and an email
    #validates and compares a provided email and password /w the dbs
    if request.form.get('email') == None or request.form.get('password') == None:
        return False
    search = get_user_by_email(request.form['email'], is_jobtaker)
    if(search == None):
        return False
    (user_session, user) = (search[0], search[1].first())
    user_session.close()
    search = passwords.get_password_by_id(user.id, is_jobtaker)
    if(search == None):
        password_session.close()
        return False
    (password_session, password) = (search[0], search[1].first())
    password_session.close()
    if not password.check_password_hash(request.form['password']):
        return False
    session['account_type'] = (lambda x : global_objects.JOBTAKER_SESSION_NAME if x else global_objects.JOBMAKER_SESSION_NAME)(is_jobtaker)
    login_user(user, remember=True)
    identity_changed.send(app, identity=Identity(user.id))
    return True

def verify_admin_login_attempt(password) -> bool:
    #checks admin login from user request
    if(global_objects.admin_password.check_password_hash(password)):
        session['account_type'] = global_objects.ADMIN_SESSION_NAME
        login_user(global_objects.admin, remember=False, duration=0)
        identity_changed.send(app, identity=Identity(global_objects.admin.id))
        return True
    else:
        return False

def register_user_account(request : Request, is_jobtaker : bool, confirmation_email : bool = True) -> bool:#request.form should contain account data and a password
    #validates, creates and adds a user+psswrd to the dbs from a user request
    #this leaves the user acc as unverified, and will be deleted after some time
    #acc creation takes a while cuz we need to verify email deliverability
    (is_valid, formated_data) = validate_user_request(request, global_objects.USER_CREATION_REQ_FORM_KEYS, True)
    if not is_valid:
        return False
    if get_user_by_email(formated_data['email'], is_jobtaker) != None:
        print("email already in use")
        return False
    if get_user_by_phone(formated_data['phone_num'], is_jobtaker) != None:
        print("phone already in use")
        return False
    user = get_user_type(is_jobtaker)(request.form['first_name'], request.form['last_name'], formated_data['email'], phonenumbers.format_number(formated_data['phone_num'], PhoneNumberFormat.E164), formated_data['country'], formated_data['city'], formated_data['birthdate'], formated_data['gender'], f"{request.form['pronouns_1']}/{request.form['pronouns_2']}")
    #add password to db
    if user == global_objects.admin:
        return False
    user_session = get_user_session(is_jobtaker)
    user_session.begin()
    if get_user_by_email(user.email, is_jobtaker) != None:
        user_session.close()
        return False
    if get_user_by_phone(user.phone_number, is_jobtaker) != None:
        user_session.close()
        return False
    user_session.add(user)
    user_session.flush()
    user_id = user.id
    if not passwords.add_user_password_to_db(user_id, request.form['password'], is_jobtaker): 
        user_session.close()
        return False
    user_session.commit()#we commit it after adding the password, to avoid desync in case of failure to commit password
    session['account_type'] = global_objects.JOBTAKER_SESSION_NAME if is_jobtaker else global_objects.JOBMAKER_SESSION_NAME
    result = send_confirmation_email(user.id, is_jobtaker)
    user_session.close()
    return result

def send_confirmation_email(user_id : int, is_jobtaker : bool) -> bool | str:#expects user to exist in db
    (db_session, query) = get_user_by_id(user_id, is_jobtaker)
    user = query.first()
    user.confirmation_email_id = 0 if user.confirmation_email_id is None else user.confirmation_email_id + 1
    days_since_reg : timedelta = user.time_registered - datetime.today().astimezone()
    if user.confirmation_email_id >= 5 * days_since_reg.days(): #allows only 5 conf email/day
        db_session.close()
        return False
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    token = serializer.dumps({"id" : user.id, "is_jobtaker" : is_jobtaker, "confirmation_email_id" : user.confirmation_email_id}, salt=global_objects.EMAIL_CONFIRMATION_SALT)
    
    if global_objects.testing:
        db_session.commit()
        db_session.close()
        return url_for('confirm_account', token=token, _external = True)
    
    mail = Mail(app)
    msg = Message(subject="Teenquest Email Confirmation", sender=app.config["MAIL_USERNAME"], recipients=[user.email])
    url = url_for('confirm_account', token=token, _external = True)
    msg.html = render_template("/email_templates/confirmation_email.html", confirmation_url=url)
    mail.send(msg)
    db_session.commit()
    db_session.close()
    return True

def confirm_user_account(token : str, expiration_time : int = 3600) -> Tuple[Any, bool] | int:
    #returns the user or a status code,
    #User is success
    #0 is failure to find user
    #1 is a wrong email id (newer token exists)
    #2 is a failure to confirm user reg
    #3 is signature expired (token to old)
    #4 is bad signature
    try:
        user_data = URLSafeTimedSerializer(app.config['SECRET_KEY']).loads(token, salt=global_objects.EMAIL_CONFIRMATION_SALT, max_age=expiration_time)
        print(user_data)
        search = get_user_by_id(user_data["id"], user_data["is_jobtaker"])
        if search is None:
            db_session.close()
            return 0
        (db_session, query) = search
        if query.first().confirmation_email_id != user_data["confirmation_email_id"]:
            db_session.close()
            return 1
        result = query.first().confirm_registration(db_session)
        if not result:
            db_session.close()
            return 2
        user = query.first()
        db_session.close()
        return (user, user_data["is_jobtaker"]) #this is the most pythonic shit ever
    except SignatureExpired:
        return 3
    except BadSignature:
        return 4
    
def delete_unconfirmed_users() -> bool:
    print("deleting unconf users")
    with app.app_context():
        i = 0
        while i < 2:#i = 0 checks jobmakers and i = 1 checks jobtakers
            user_type = get_user_type(bool(i))
            db_session = get_user_session(bool(i))
            db_session.begin()
            query = db_session.query(user_type.id).filter(
                user_type.time_confirmed == None,
                user_type.time_registered < (datetime.now().astimezone() - timedelta(days=3)))
            user_ids : List[int] = [row.id for row in query.all()]
            db_session.query(user_type).filter(user_type.id.in_(user_ids)).delete()
            db_session.commit()
            passwords.delete_passwords_by_ids(user_ids, bool(i))
            print(f"wiped {len(user_ids)} {"jobtakers" if bool(i) else "jobmakers"}")
            i += 1
            db_session.close()
    return True

@identity_loaded.connect
def on_identity_loaded(sender, identity):
    #loads roles to user
    identity.user = current_user
    if hasattr(identity.user, "id"):
        identity.provides.add(UserNeed(identity.user.id))
    if hasattr(identity.user, "roles"):
        for role in identity.user.roles:
            identity.provides.add(role)
    if global_objects.testing:
        print(identity.provides)