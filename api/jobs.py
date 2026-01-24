#Imports
from datetime import datetime, timezone
from typing import List
from flask import Flask, session
import passwords
from sqlalchemy.orm import sessionmaker, Session
import global_objects
from global_objects import db, JobState
from sqlalchemy_utils import CountryType, Country
from decimal import Decimal, getcontext, localcontext
from users import get_user_by_id

#handles password checking, hashing, and password db operations(add, edit, delete)

app : Flask

sessionmaker_job : sessionmaker
def init_module(application):
    #initializes the jobs module
    with application.app_context():
        global app
        app = application
        global sessionmaker_job
        sessionmaker_job = sessionmaker(bind=db.engines["jobs"])
        global_objects.job_type = Job

class Job(db.Model):
    __bind_key__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    jobtaker_id = db.Column(db.Integer, nullable=True)
    jobmaker_id = db.Column(db.Integer, nullable=False)
    job_state = db.Column(db.Enum(JobState), default=JobState.CREATED, nullable=False)
    date_time_created = db.Column(db.DateTime, default=datetime.now(timezone.utc).astimezone(), nullable=False)
    date_time_accepted_taker = db.Column(db.DateTime, nullable=True)
    date_time_accepted_maker = db.Column(db.DateTime, nullable=True)
    date_time_started = db.Column(db.DateTime, nullable=True)
    date_time_ended = db.Column(db.DateTime, nullable=True)
    date_time_payed = db.Column(db.DateTime, nullable=True)
    job_type = db.Column(db.String(30), nullable=False)
    date_time_scheduled_start = db.Column(db.DateTime, default=datetime.min, nullable=False) #schelduled = when the job should be started/ended (entered by jobmaker)
    date_time_scheduled_end = db.Column(db.DateTime, default=datetime.min, nullable=False)
    country = db.Column(CountryType, nullable=False)
    city = db.Column(db.String(200), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    street = db.Column(db.String(200), nullable=False)
    job_title = db.Column(db.String(50), nullable=False)
    job_description = db.Column(db.String(500), nullable=False)
    job_salary = db.Column(db.Float(asdecimal=True), nullable=False)
    
    def __init__(self, jobmaker_id, job_type, date_time_scheduled_start, date_time_scheduled_end, country, city, zip_code, street, job_title, job_description, job_salary):
        self.jobmaker_id = jobmaker_id
        self.job_type = job_type
        self.date_time_scheduled_start = date_time_scheduled_start
        self.date_time_scheduled_end = date_time_scheduled_end
        self.country = country
        self.city = city
        self.zip_code = zip_code
        self.street = street
        self.job_title = job_title
        self.job_description = job_description
        self.job_salary = job_salary
        
    def __repr__(self) -> str:
        return f"""Job{'\n'}{self.id}{'\n'}{self.jobtaker_id}{'\n'}{self.jobmaker_id}{'\n'}{self.job_state}{'\n'}{self.date_time_created}{'\n'}{self.date_time_accepted_taker}{'\n'}
        {self.date_time_accepted_maker}{'\n'}{self.date_time_started}{'\n'}{self.date_time_ended}{'\n'}{self.date_time_payed}{'\n'}{self.job_type}{'\n'}{self.date_time_scheduled_start}{'\n'}
        {self.date_time_scheduled_end}{'\n'}{self.country}, {self.city}, {self.street}, {self.zip_code}{'\n'}{self.job_title}{'\n'}{self.job_description}{'\n'}, {self.job_salary}{'\n'}"""

def get_all_jobtaker_jobs(user) -> List[Job] | None:
    #gets all jobs assigned to a jobtaker
    if not isinstance(user, global_objects.jobtaker_type):
        return None
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.jobmaker_id == user.id)
    if query.count() == 0:
        return None
    else:
        return query.all()
    
def get_all_jobmaker_jobs(user) -> List[Job] | None:
    #gets all jobs assigned to a jobmaker
    if not isinstance(user, global_objects.jobmaker_type):
        return None
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.jobmaker_id == user.id)
    if query.count() == 0:
        return None
    else:
        return query.all()

def get_job_by_id(job_id) -> Job | None:
    #gets job from db by id
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.id == job_id)
    if query.count() != 1:
        return None
    return query.first()

def create_job(user, request) -> bool:
    #validates and creates a job from a user request
    if not validate_job_request(request):
        return False
    if user != global_objects.admin and get_user_by_id(user.id, False) != user:
        return False
    job = Job(user.id, request.form['job_type'], datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M"),
            datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M"), Country(request.form['country']), request.form['city'], request.form['zip_code'], request.form['street'], request.form['job_title'],
            request.form['job_description'], Decimal(request.form['job_salary']))
    return add_job_to_db(job)
    

def add_job_to_db(job : Job) -> bool:
    #add a job to the jobs db
    db_session : Session = sessionmaker_job()
    db_session.begin()
    db_session.add(job)
    db_session.commit()
    return True

def update_job_state(job_id, job_state) -> bool:
    #"progresses" job forward (reffer to chart)
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.id == job_id)
    if query.count() != 1:
        return False
    if(job_state.value - 1 != query.first().job_state.value):
        return False
    match(job_state):
        case JobState.CREATED:
            query.update({Job.job_state : job_state, Job.date_time_created : datetime.now(timezone.utc).astimezone()})
        case JobState.ACCEPTED_TAKER:
            query.update({Job.job_state : job_state, Job.date_time_accepted_taker : datetime.now(timezone.utc).astimezone()})
        case JobState.ACCEPTED_MAKER:
            query.update({Job.job_state : job_state, Job.date_time_accepted_maker : datetime.now(timezone.utc).astimezone()})
        case JobState.STARTED:
            query.update({Job.job_state : job_state, Job.date_time_started : datetime.now(timezone.utc).astimezone()})
        case JobState.ENDED:
            query.update({Job.job_state : job_state, Job.date_time_ended : datetime.now(timezone.utc).astimezone()})
        case JobState.PAYED:
            query.update({Job.job_state : job_state, Job.date_time_payed : datetime.now(timezone.utc).astimezone()})
            db_session.flush()
            query = db_session.query(Job).filter(Job.job_state == JobState.PAYED)
            if query.count() > 5:
                query.order_by(Job.date_time_payed).limit(query.count()-5).delete()
    db_session.commit()
    return True

def edit_job(user, request) -> bool:
    #validates and changes user accessible job data from a user request if job isn't locked
    if not validate_job_request(request):
        return False
    if user != global_objects.admin and get_user_by_id(user.id, False) != user:
        return False
    job_id = None
    try:
        job_id = int(request.form['job_id'])
    except TypeError as e:
        print(e)
        return False
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.id == job_id)
    if query.count() != 1:
        return False
    job = query.first()
    if job.job_state.value > JobState.ACCEPTED_MAKER.value:#if job_state is alr accepted, block job editing
        return False
    query.update({
        Job.job_type : request.form['job_type'],
        Job.date_time_scheduled_start : datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M"),
        Job.date_time_scheduled_end : datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M"),
        Job.country : Country(request.form['country']),
        Job.city : request.form['city'],
        Job.zip_code : request.form['zip_code'],
        Job.street : request.form['street'],
        Job.job_title : request.form['job_title'],
        Job.job_description : request.form['job_description'],
        Job.job_salary : Decimal(request.form['job_salary'])
    })
    db_session.commit()
    return True

def delete_job(job_id : Job) -> bool:
    #deletes job if it isn't locked
    job = get_job_by_id(job_id)
    if job == None or job.job_state.value > JobState.ACCEPTED_MAKER.value:#if job_state is alr accepted, block job deletion
        return False
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.id == job.id)
    if query.count() > 0:
        query.delete()
    db_session.commit()
    return True

def validate_job_request(request) -> bool:
    #checks if request.form contains parsable information
    def handle_error(e):
        print(e)
        return False
    try:
        job_scheduled_start = datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M")
    except ValueError as e:
        return handle_error(e)
    try:
        job_scheduled_end = datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M")
    except ValueError as e:
        return handle_error(e)
    if job_scheduled_start > job_scheduled_end:
        return handle_error("dates got fd upp")
    try:
        Country(request.form['country'])
    except ValueError as e:
        return handle_error(e)
    #todo:address validation
    try:
        Decimal(request.form['job_salary'])
    except Exception as e:
        return handle_error(e)
    return True
    