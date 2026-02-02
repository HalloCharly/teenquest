from global_objects import JOBTAKERS_BINDKEY, JOBMAKERS_BINDKEY, JOBTAKER_PASSWORDS_BINDKEY, JOBMAKER_PASSWORDS_BINDKEY, JOBS_BINDKEY, LOGS_BINDKEY
from datetime import timedelta

SECRET_KEY = "epstein grape chiggers"

SQLALCHEMY_DATABASE_URI = "sqlite:///jobs.db"
SQLALCHEMY_BINDS = {
    JOBTAKERS_BINDKEY: "sqlite:///users.db",
    JOBMAKERS_BINDKEY: "sqlite:///users.db",
    JOBTAKER_PASSWORDS_BINDKEY: "sqlite:///passwords.db",
    JOBMAKER_PASSWORDS_BINDKEY: "sqlite:///passwords.db",
    JOBS_BINDKEY: "sqlite:///jobs.db",
    LOGS_BINDKEY: "sqlite:///logs.db"
}

SQLALCHEMY_TRACK_MODIFICATIONS = False

REMEMBER_COOKIE_DURATION = timedelta(weeks=5)
PERMANENT_SESSION_LIFETIME = timedelta(weeks=5)

REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
SESSION_REFRESH_EACH_REQUEST = True

MAIL_SERVER = 'smtp.office365.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = "teenquest.production@outlook.com"
MAIL_PASSWORD = "pendulum1234"