#Imports
from secrets import choice
import string
from hashlib import sha3_256
from flask import Flask
from flask_login import UserMixin
from sqlalchemy.orm import sessionmaker, Session
import global_objects
from global_objects import db

app : Flask

def init_module(application):
    #initializes the passwords module
    with application.app_context():
        global app
        app = application
        global sessionmaker_jobtakerpassword
        sessionmaker_jobtakerpassword = sessionmaker(bind=db.engines['jobtaker_passwords'])
        global sessionmaker_jobmakerpassword
        sessionmaker_jobmakerpassword = sessionmaker(bind=db.engines['jobmaker_passwords'])
        global_objects.jobtaker_password_type = JobTakerPassword
        global_objects.jobmaker_password_type = JobMakerPassword

admin_password_hash = "c31083adbb87e2490499a657d7f790dbfa7571f5f639b64c1e6ce44d7f06c4d2"#todo:move into cfg file or smwhere idk

def password_model_factory(bind_key):
    #creates a password class/db model
    class DynamicPassword(db.Model, UserMixin):
        __bind_key__ = bind_key
        __tablename__ = bind_key
        user_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
        password_hash = db.Column(db.String, nullable=False)
        salt = db.Column(db.String(16), nullable=False)
    
        def __init__(self, user_id, password_hash, salt):
            self.user_id = user_id
            self.password_hash = password_hash
            self.salt = salt

        def __repr__(self) -> str:
            return f"""Password{'\n'}{self.user_id}{'\n'}{self.password_hash}{'\n'}{self.salt}{'\n'}"""

    return DynamicPassword

JobTakerPassword = password_model_factory("jobtaker_passwords")
JobMakerPassword = password_model_factory("jobmaker_passwords")

def get_password_type(is_jobtaker):
    #returns the password type for jobtakers or jobmakers
    if is_jobtaker:
        return JobTakerPassword
    else:
        return JobMakerPassword

def get_password_session(is_jobtaker) -> Session:
    #returns a db session for jobtakers or jobmakers
    if is_jobtaker:
        return sessionmaker_jobtakerpassword()
    else:
        return sessionmaker_jobmakerpassword()

def get_password_by_id(user_id, is_jobtaker):
    #gets the password for a user id
    if user_id == 0:
        return admin_password_hash
    else:
        db_session = get_password_session(is_jobtaker)
        db_session.begin()
        user_type = get_password_type(is_jobtaker)
        query = db_session.query(user_type).filter(user_type.user_id == user_id)
        if query.count() != 1:
            return None
        return query.first()

def check_password_hash(user, password, is_jobtaker) -> bool:
    #salts and hashes a password from a user request and compares it with the hash in the db
    if user == global_objects.admin:#admin check
        return generate_password_hash(password, "") == admin_password_hash
    else:
        db_session = get_password_session(is_jobtaker)
        db_session.begin()
        user_type = get_password_type(is_jobtaker)
        query = db_session.query(user_type).filter(user_type.user_id == user.id)
        if query.count() != 1:
            return False
        return generate_password_hash(password, query.first().salt) == query.first().password_hash

def generate_salt(char_ammount=16) -> str:
    #creates a random salt for a user
    chars = string.ascii_letters + string.digits
    return ''.join(choice(chars) for _ in range(char_ammount))

def generate_password_hash(password, salt) -> str:
    #takes in a password and salt and returns their hash
    hash = sha3_256()
    hash.update((password + salt).encode('utf-8'))
    return hash.hexdigest()

def edit_password(user_id, password, is_jobtaker) -> bool:
    #changes a user's password hash present in the passwords db
    password_type = get_password_type(is_jobtaker)
    db_session = get_password_session(is_jobtaker)
    db_session.begin()
    query = db_session.query(password_type).filter(password_type.user_id==user_id)
    query.update({
        password_type.password_hash: generate_password_hash(password, query.first().salt)
    })
    db_session.commit()
    return True
    
def delete_password(user_id, session_type) -> bool:
    #deletes a user password from passwords db
    if user_id == global_objects.admin.id or session_type == "admin":
        return False
    if session_type != "jobtaker" and session_type != "jobmaker":
        return False
    password_type = get_password_type(session_type == "jobtaker")
    db_session = get_password_session(session_type == "jobtaker")
    db_session.begin()
    db_session.query().filter(password_type.user_id == user_id).limit(1).delete()
    db_session.commit()
    return True

def add_user_password_to_db(user_id, password, is_jobtaker, force_add=False) -> bool:
    #add a password to the passwords db
    db_session = get_password_session(is_jobtaker)
    db_session.begin()
    if get_password_by_id(user_id, is_jobtaker) != None and not force_add:
        return False
    salt = generate_salt()
    db_session(get_password_type(is_jobtaker)(user_id, generate_password_hash(password, salt), salt))
    db_session.commit()
    return True