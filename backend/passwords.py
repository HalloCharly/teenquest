#Imports
from secrets import choice
import string
from hashlib import sha3_256
from typing import Any, List, Tuple
from flask import Flask
from flask_login import UserMixin
from sqlalchemy.orm import sessionmaker, Session, Query
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
        global_objects.make_admin_password_object(AdminPassword)
        global_objects.jobtaker_password_type = JobTakerPassword
        global_objects.jobmaker_password_type = JobMakerPassword

def password_model_factory(bind_key):
    #creates a password class/db model
    class DynamicPassword(db.Model, UserMixin):
        __bind_key__ = bind_key
        __tablename__ = bind_key
        id = db.Column(db.Integer(), primary_key=True, autoincrement=False)
        password_hash = db.Column(db.String(), nullable=False)
        salt = db.Column(db.String(16), nullable=False)
    
        def __init__(self, user_id, password_hash, salt):
            self.id = user_id
            self.password_hash = password_hash
            self.salt = salt

        def __repr__(self) -> str:
            return f"""Password{'\n'}{self.id}{'\n'}{self.password_hash}{'\n'}{self.salt}{'\n'}"""


        def check_password_hash(self, password : str) -> bool:
            #salts and hashes a password from a user request and compares it with the hash in the db
                return generate_password_hash(password, self.salt) == self.password_hash
        
        def edit_password(self, password : str, db_session : Session = None) -> bool:
            #changes a user's password hash present in the passwords db
            if self == global_objects.admin_password:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_password_session(self.__bind_key__ == global_objects.JOBTAKER_PASSWORDS_BINDKEY)
                db_session.begin()
            self.password_hash = generate_password_hash(password, self.salt)
            if db_was_empty:
                db_session.commit()
                db_session.close()
            return True
            
        def delete_password(self, db_session : Session = None) -> bool:
            #deletes a user password from passwords db
            if self == global_objects.admin_password:
                return False
            db_was_empty = db_session == None
            if db_was_empty:
                db_session = get_password_session(self.__bind_key__ == global_objects.JOBTAKER_PASSWORDS_BINDKEY)
                db_session.begin()
            db_session.delete(self)
            if db_was_empty:
                db_session.commit()
                db_session.close()
            return True
    return DynamicPassword

JobTakerPassword = password_model_factory(global_objects.JOBTAKER_PASSWORDS_BINDKEY)
JobMakerPassword = password_model_factory(global_objects.JOBMAKER_PASSWORDS_BINDKEY)
AdminPassword = password_model_factory("_")

def get_password_type(is_jobtaker : bool):
    #returns the password type for jobtakers or jobmakers
    if is_jobtaker:
        return JobTakerPassword
    else:
        return JobMakerPassword

def get_password_session(is_jobtaker : bool) -> Session:
    #returns a db session for jobtakers or jobmakers
    if is_jobtaker:
        return sessionmaker_jobtakerpassword()
    else:
        return sessionmaker_jobmakerpassword()

def get_password_by_id(user_id : int, is_jobtaker : bool) -> Tuple[Session, Query[Any]] | Any | None:
    #gets the password for a user id
    if user_id == global_objects.admin.id:
        return global_objects.admin_password
    else:
        db_session = get_password_session(is_jobtaker)
        db_session.begin()
        user_type = get_password_type(is_jobtaker)
        query = db_session.query(user_type).filter(user_type.id == int(user_id))
        if query.count() != 1:
            db_session.close()
            return None
        return (db_session, query)
def generate_salt(char_ammount : int = 16) -> str:
    #creates a random salt for a user
    chars = string.ascii_letters + string.digits
    return ''.join(choice(chars) for _ in range(char_ammount))

def generate_password_hash(password : str, salt : str) -> str:
    #takes in a password and salt and returns their hash
    hash = sha3_256()
    hash.update((password + salt).encode('utf-8'))
    return hash.hexdigest()

def add_user_password_to_db(user_id : int, password : str, is_jobtaker : bool, force_add : bool = False) -> bool:
    #add a password to the passwords db
    db_session = get_password_session(is_jobtaker)
    db_session.begin()
    if get_password_by_id(user_id, is_jobtaker) != None and not force_add:
        db_session.close()
        return False
    salt = generate_salt()
    db_session.add(get_password_type(is_jobtaker)(user_id, generate_password_hash(password, salt), salt))
    db_session.commit()
    db_session.close()
    return True

def delete_passwords_by_ids(user_ids : List[int], is_jobtaker : bool) -> bool:
    db_session = get_password_session(is_jobtaker)
    user_type = get_password_type(is_jobtaker)
    db_session.begin()
    db_session.query(user_type).filter(user_type.id.in_(user_ids)).delete()
    db_session.commit()
    db_session.close()
    return True