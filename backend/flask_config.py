from flask import Flask

from global_objects import JOBTAKERS_BINDKEY, JOBMAKERS_BINDKEY, JOBTAKER_PASSWORDS_BINDKEY, JOBMAKER_PASSWORDS_BINDKEY, JOBS_BINDKEY, LOGS_BINDKEY
from datetime import timedelta
from dotenv import load_dotenv
from os import environ

#holds some of the config for the flask app

def load_env_config(app : Flask): #loads config from 
    load_dotenv("../")
    app.config["SECRET_KEY"] = environ['FLASK_SECRET_KEY']
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg://{environ['DATABASE_URL']}/jobs"
    app.config["SQLALCHEMY_BINDS"] = {
        JOBTAKERS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/users",
        JOBMAKERS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/users",
        JOBTAKER_PASSWORDS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/passwords",
        JOBMAKER_PASSWORDS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/passwords",
        JOBS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/jobs",
        LOGS_BINDKEY: f"postgresql+psycopg://{environ['DATABASE_URL']}/logs"
    }
    app.config["MAIL_SERVER"] = environ['MAIL_SERVER']
    app.config["MAIL_PORT"] = int(environ['MAIL_PORT'])
    app.config["MAIL_USERNAME"] = environ['MAIL_USERNAME']
    app.config["MAIL_PASSWORD"] = environ['MAIL_PASSWORD']
    
SQLALCHEMY_TRACK_MODIFICATIONS = False

REMEMBER_COOKIE_DURATION = timedelta(weeks=5)
PERMANENT_SESSION_LIFETIME = timedelta(weeks=5)

REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
SESSION_REFRESH_EACH_REQUEST = True

MAIL_USE_TLS = True
MAIL_USE_SSL = False
