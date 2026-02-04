#Imports
from datetime import datetime, timezone
from typing import List, Tuple
from flask import Flask, Request, session
from sqlalchemy import desc
import passwords
from sqlalchemy.orm import sessionmaker, Session, Query
import global_objects
from global_objects import db, JobState, JobFilter
from sqlalchemy_utils import CountryType, Country
from decimal import Decimal
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
        sessionmaker_job = sessionmaker(bind=db.engines[global_objects.JOBS_BINDKEY])
        global_objects.job_type = Job

class Job(db.Model):
    __bind_key__ = "jobs"
    id = db.Column(db.Integer(), primary_key=True)
    jobtaker_id = db.Column(db.Integer(), nullable=True)
    jobmaker_id = db.Column(db.Integer(), nullable=False)
    jobmaker_rating = db.Column(db.Integer(), nullable=True)
    job_state = db.Column(db.Enum(JobState), default=JobState.CREATED, nullable=False)
    date_time_created = db.Column(db.DateTime(), default=datetime.now(timezone.utc).astimezone(), nullable=False)
    date_time_accepted_taker = db.Column(db.DateTime(), nullable=True)
    date_time_accepted_maker = db.Column(db.DateTime(), nullable=True)
    date_time_started = db.Column(db.DateTime(), nullable=True)
    date_time_ended = db.Column(db.DateTime(), nullable=True)
    date_time_payed = db.Column(db.DateTime(), nullable=True)
    job_type = db.Column(db.String(30), nullable=False)
    date_time_scheduled_start = db.Column(db.DateTime(), default=datetime.min, nullable=False) #schelduled = when the job should be started/ended (entered by jobmaker)
    date_time_scheduled_end = db.Column(db.DateTime(), default=datetime.min, nullable=False)
    country = db.Column(CountryType, nullable=False)
    city = db.Column(db.String(200), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    street = db.Column(db.String(200), nullable=False)
    job_title = db.Column(db.String(50), nullable=False)
    job_description = db.Column(db.String(500), nullable=False)
    job_salary = db.Column(db.Float(asdecimal=True), nullable=False)
    
    def __init__(self, jobmaker_id, jobmaker_rating, job_type, date_time_scheduled_start, date_time_scheduled_end, country, city, zip_code, street, job_title, job_description, job_salary):
        self.jobmaker_id = jobmaker_id
        self.jobmaker_rating = jobmaker_rating
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

    def edit_job(self, request : Request, db_session : Session | None = None, commit : bool = True) -> bool:
        #validates and changes user accessible job data from a user request if job isn't locked
        if not validate_job_request(request):
            return False
        db_was_empty = db_session == None
        if db_was_empty:
            db_session : Session = sessionmaker_job()
            db_session.begin()
        if self.job_state.value >= JobState.ACCEPTED_MAKER.value:#if job_state is alr accepted, block job editing
            return False
        db_session.query(Job).filter(Job.id == int(self.id)).update({
            Job.job_type : request.form['job_type'],
            Job.date_time_scheduled_start : datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M").astimezone(),
            Job.date_time_scheduled_end : datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M").astimezone(),
            Job.country : Country(request.form['country']),
            Job.city : request.form['city'],
            Job.zip_code : request.form['zip_code'],
            Job.street : request.form['street'],
            Job.job_title : request.form['job_title'],
            Job.job_description : request.form['job_description'],
            Job.job_salary : Decimal(request.form['job_salary'])
        })
        db_session.flush()
        #self.job_type = request.form['job_type']
        #self.date_time_scheduled_start = datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M")
        #self.date_time_scheduled_end = datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M")
        #self.country = Country(request.form['country'])
        #self.city = request.form['city']
        #self.zip_code = request.form['zip_code']
        #self.street = request.form['street']
        #self.job_title = request.form['job_title']
        #self.job_description = request.form['job_description']
        #self.job_salary = Decimal(request.form['job_salary'])
        if db_was_empty or commit:
            db_session.commit()
        return True
    
    def deny_jobtaker_job_state(self : Session | None = None, commit : bool = True):
        if self.job_state != global_objects.JobState.ACCEPTED_TAKER:
            return False
        db_was_empty = db_session == None
        if db_was_empty:
            db_session : Session = sessionmaker_job()
            db_session.begin()
        self.job_state = JobState.CREATED
        self.jobtaker_id = None
        self.date_time_accepted_taker = None
        if db_was_empty or commit:
            db_session.commit()
        
    def progress_job_state(self, job_state : JobState, rating : int | None = None, jobtaker_id : int | None = None, db_session : Session | None = None, commit : bool = True) -> bool:
        #"progresses" job forward (reffer to chart)
        db_was_empty = db_session == None
        if db_was_empty:
            db_session : Session = sessionmaker_job()
            db_session.begin()
        if job_state.value - 1 != self.job_state.value:
            return False
        self.job_state = job_state
        match job_state:
            case JobState.CREATED:
                self.date_time_created = datetime.now(timezone.utc).astimezone()
            case JobState.ACCEPTED_TAKER:
                if jobtaker_id == None:
                    print("Failed to provide jobtaker_id to jobstate progressor")
                    return False
                self.jobtaker_id = jobtaker_id
                self.date_time_accepted_taker = datetime.now(timezone.utc).astimezone()
            case JobState.ACCEPTED_MAKER:
                self.date_time_accepted_maker = datetime.now(timezone.utc).astimezone()
            case JobState.STARTED:
                self.date_time_started = datetime.now(timezone.utc).astimezone()
            case JobState.ENDED:
                if rating == None:
                    print("Failed to provide rating to jobstate progressor")
                    return False
                self.date_time_ended = datetime.now(timezone.utc).astimezone()
                search = get_user_by_id(self.jobmaker_id, False)
                if search != None:
                    (user_session, user_query) = search
                    user_query.first().change_rating(rating, user_session)
                    update_jobs_ratings(user_query.first())
            case JobState.PAYED:
                if rating == None:
                    print("Failed to provide rating to jobstate progressor")
                    return False
                self.date_time_payed = datetime.now(timezone.utc).astimezone()
                db_session.flush()
                query = db_session.query(Job.id).filter(Job.job_state == JobState.PAYED)
                if query.count() > 5:
                    sub_query = query.order_by(Job.date_time_payed).limit(query.count()-5).subquery()
                    db_session.query(Job).filter(Job.id.in_(sub_query)).delete()
                search = get_user_by_id(self.jobtaker_id, True)
                if search != None:
                    (jobtaker_session, jobtaker_query) = search
                    jobtaker_query.first().change_rating(rating, jobtaker_session, commit = False)
                    jobtaker_query.first().increment_job_ammount_done(jobtaker_session)
                search = get_user_by_id(self.jobmaker_id, False)
                if search != None:
                    (jobmaker_session, jobmaker_query) = search
                    jobmaker_query.first().increment_job_ammount_done(jobmaker_session)
        if db_was_empty or commit:
            db_session.commit()
        return True

    def delete_job(self, db_session : Session | None = None, commit : bool = True) -> bool:
        #deletes job if it isn't locked
        if self.job_state.value >= JobState.ACCEPTED_MAKER.value:#if job_state is alr accepted, block job editing
            return False
        db_was_empty = db_session == None
        if db_was_empty:
            db_session = sessionmaker_job()
            db_session.begin()
        db_session.delete(self)
        if db_was_empty or commit:
            db_session.commit()
        return True

def get_all_jobtaker_jobs(user) -> Tuple[Session, Query[Job]] | None:
    #returns a session and query with all of a jobtaker's jobs
    if not isinstance(user, global_objects.jobtaker_type):
        return None
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.jobmaker_id == int(user.id))
    if query.count() == 0:
        return None
    else:
        return (db_session, query)
    
def get_all_jobmaker_jobs(user) -> Tuple[Session, Query[Job]] | None:
    #returns a session and query with all of a jobmaker's jobs
    if not isinstance(user, global_objects.jobmaker_type):
        return None
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.jobmaker_id == int(user.id))
    if query.count() == 0:
        return None
    else:
        return (db_session, query)

def get_job_by_id(job_id : int) -> Tuple[Session, Query[Job]] | None:
    #gets job from db by id
    db_session : Session = sessionmaker_job()
    db_session.begin()
    query = db_session.query(Job).filter(Job.id == int(job_id))
    if query.count() != 1:
        return None
    return (db_session, query)

def create_job(user, request : Request) -> bool:
    #validates and creates a job from a user request
    if not validate_job_request(request):
        return False
    search = get_user_by_id(user.id, False)
    if search == None:
        return False
    if user != global_objects.admin and search[1].first() != user:
        return False
    job = Job(user.id, user.rating_avg, request.form['job_type'], datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M").astimezone(),
            datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M").astimezone(), Country(request.form['country']), request.form['city'], request.form['zip_code'], request.form['street'], request.form['job_title'],
            request.form['job_description'], Decimal(request.form['job_salary']))
    db_session : Session = sessionmaker_job()
    db_session.begin()
    db_session.add(job)
    db_session.commit()
    return True

def update_jobs_ratings(user) -> bool:
    #gets all jobs belonging to a user and updates their ratings to the user's rating
    jobs = get_all_jobmaker_jobs(user)
    if jobs == None:
        return False
    (db_session, query) = jobs
    query.filter(Job.job_state != int(JobState.PAYED))
    query.update({Job.jobmaker_rating : user.rating_avg})
    db_session.commit()
    return True

def validate_job_request(request : Request) -> bool:
    #checks if request.form contains parsable information
    def handle_error(e):
        print(e)
        return False
    try:
        job_scheduled_start = datetime.strptime(request.form['job_scheduled_start'], "%Y-%m-%dT%H:%M").astimezone()
    except ValueError as e:
        return handle_error(e)
    try:
        job_scheduled_end = datetime.strptime(request.form['job_scheduled_end'], "%Y-%m-%dT%H:%M").astimezone()
    except ValueError as e:
        return handle_error(e)
    if job_scheduled_start > job_scheduled_end:
        return handle_error("dates got fd upp")
    if job_scheduled_end < datetime.now(timezone.utc).astimezone():
        return handle_error("cant make job start before today")
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

def get_filtered_jobs(user, request : Request, row_count : int = 20) -> Query[Job] | None:
    db_session : Session = sessionmaker_job()
    db_session.begin()
    try:
        job_filter = JobFilter(int(request.form['job_filter']))
    except ValueError as e:
        print(e)
        return None
    query = db_session.query(Job)
    match job_filter:
        case JobFilter.DEFAULT | _:
            query.filter(Job.country == user.country)
            query.order_by(desc(Job.jobmaker_rating))
            #filter by city prox here plzzz
            query.limit(row_count)
    return query
            