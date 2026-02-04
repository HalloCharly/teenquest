from global_objects import JOBTAKERS_BINDKEY, JOBMAKERS_BINDKEY, JOBTAKER_PASSWORDS_BINDKEY, JOBMAKER_PASSWORDS_BINDKEY, JOBS_BINDKEY, LOGS_BINDKEY
from datetime import timedelta

SECRET_KEY = "epstein grape chiggers"

SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://postgres:Kutas001@localhost:5432/jobs"
SQLALCHEMY_BINDS = {
    JOBTAKERS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/users",
    JOBMAKERS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/users",
    JOBTAKER_PASSWORDS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/passwords",
    JOBMAKER_PASSWORDS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/passwords",
    JOBS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/jobs",
    LOGS_BINDKEY: "postgresql+psycopg://postgres:Kutas001@localhost:5432/logs"
}

SQLALCHEMY_TRACK_MODIFICATIONS = False

REMEMBER_COOKIE_DURATION = timedelta(weeks=5)
PERMANENT_SESSION_LIFETIME = timedelta(weeks=5)

REMEMBER_COOKIE_REFRESH_EACH_REQUEST = True
SESSION_REFRESH_EACH_REQUEST = True

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = "teenquest.prod@gmail.com"
MAIL_PASSWORD = "vzvg alzt vabh eusa"
