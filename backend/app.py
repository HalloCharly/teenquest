#Imports
import global_objects as global_objects
from datetime import datetime, timezone
from enum import Enum

import passwords
from users import (init_module as user_init_module,
                   validate_login_attempt as user_validate_login_attempt,
                   create_account as user_create_account,
                   validate_admin_login as user_validate_admin_login,
                   on_identity_loaded as user_on_identity_loaded,
                   get_user_by_id)
import jobs
from global_objects import db, login_manager, admin_permission, jobtaker_permission, jobmaker_permission, JobState
from flask import Flask, flash, render_template, redirect, request, session, url_for
from sqlalchemy.orm import sessionmaker
from flask_login import current_user, login_required, logout_user
from flask_principal import identity_changed, AnonymousIdentity, identity_loaded

#main app file

#App
app = Flask(__name__, template_folder='../test_html/')

app.secret_key = "epstein grape chiggers"#todo:move into cfg file

login_manager.init_app(app)

#Db setupa
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_BINDS"] = {
    global_objects.JOBTAKERS_BINDKEY: "sqlite:///users.db",
    global_objects.JOBMAKERS_BINDKEY: "sqlite:///users.db",
    global_objects.JOBTAKER_PASSWORDS_BINDKEY: "sqlite:///passwords.db",
    global_objects.JOBMAKER_PASSWORDS_BINDKEY: "sqlite:///passwords.db",
    global_objects.JOBS_BINDKEY: "sqlite:///jobs.db",
    global_objects.LOGS_BINDKEY: "sqlite:///logs.db"
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

#initialize all of the modules
user_init_module(app)
passwords.init_module(app)
jobs.init_module(app)
global_objects.setup_principals(app)
    
class Log(db.Model):
    __bind_key__ = global_objects.LOGS_BINDKEY
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, nullable=False) #we set the ids to positive if its a jbmaker, and negative if its a jbtaker
    recipient_id = db.Column(db.Integer, nullable=False)
    date_time_sent = db.Column(db.DateTime, default=datetime.now(timezone.utc).astimezone(), nullable=False)
    content = db.Column(db.String, nullable=False)
    
    def __init__(self, sender_id, recipient_id, date_time_sent, content):
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.date_time_sent = date_time_sent
        self.content = content
        
    def __repr__(self) -> str:
        return f"Log{'\n'}{self.id}{'\n'}{self.sender_id}{'\n'}{self.recipient_id}{'\n'}{self.date_time_sent}{'\n'}{self.content}{'\n'}"

def test_log(force):#adds 1 placeholder log || ts is temporary, jus using this for now
    db_session = sessionmaker(bind=db.engines[global_objects.LOGS_BINDKEY])()
    db_session.begin()
    if db_session.query(Log).filter(Log.sender_id == 1).count() == 0 or force:
        db_session.add(Log(1, -1, datetime.min, "i will do something brand safe to u"))
    db_session.commit()
    
with app.app_context():
    db.create_all(bind_key=global_objects.DB_BINDKEYS_TO_CREATE)
    #test_job(False)
    test_log(False)




#Main navigation
@app.route("/", methods=["GET"])
def index_page():
    return render_template("index.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")



#General Utilities
@app.route('/logout', methods=["GET"])
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(app, identity=AnonymousIdentity())
    session['account_type'] = global_objects.ANONYMOUS_SESSION_NAME
    return redirect(url_for("index_page"))

@app.route('/delete', methods=["GET"])
@login_required
def delete():
    user = current_user
    user.delete_account()
    print(user.first_name)
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(app, identity=AnonymousIdentity())
    session['account_type'] = global_objects.ANONYMOUS_SESSION_NAME
    return redirect(url_for("index_page"))



#JobTaker account management
@app.route("/jobtaker/login", methods=["GET", "POST"])
def login_jobtaker():
    if(request.method == "POST"):
        if(user_validate_login_attempt(request, True)):
            return redirect(url_for('jobmarket_jobtaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobtaker.html"), 401
    else:
        return render_template("login_jobtaker.html")

@app.route("/jobtaker/edit", methods=["GET", "POST"])
@jobtaker_permission.require(http_exception=401)
@login_required
def edit_account_jobtaker():
    if(request.method == "POST"):
        if(current_user.edit_account(request)):
            return redirect(url_for('jobmarket_jobtaker_page'))
        else:
            flash("looser", "error")
            return render_template("edit_jobtaker.html"), 401
    else:
        return render_template("edit_jobtaker.html")
    
@app.route("/jobtaker/create", methods=["GET", "POST"])
def create_account_jobtaker():
    if(request.method == "POST"):
        if(user_create_account(request, True)):
            return redirect(url_for("login_jobtaker"))
        else:
            return redirect(url_for("create_account_jobtaker")), 401
    else:
        return render_template("create_jobtaker.html")



#JobMaker account management
@app.route("/jobmaker/login", methods=["GET", "POST"])
def login_jobmaker():
    if(request.method == "POST"):
        if(user_validate_login_attempt(request, False)):
            return redirect(url_for('jobmarket_jobmaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobmaker.html"), 401
    else:
        return render_template("login_jobmaker.html")
    
@app.route("/jobmaker/edit", methods=["GET", "POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def edit_account_jobmaker():
    if(request.method == "POST"):
        if(current_user.edit_account(request)):
            return redirect(url_for('jobmarket_jobmaker_page'))
        else:
            flash("looser", "error")
            return render_template("edit_jobmaker.html"), 401
    else:
        return render_template("edit_jobmaker.html")

@app.route("/jobmaker/create", methods=["GET", "POST"])
def create_account_jobmaker():
    if(request.method == "POST"):
        if(user_create_account(request, False)):
            return redirect(url_for("login_jobmaker"))
        else:
            return redirect(url_for("create_account_jobmaker")), 401
    else:
        return render_template("create_jobmaker.html")



#Admin view
@app.route("/admin/login", methods=["GET", "POST"])
def login_admin():
    if(request.method == "POST"):
        if(user_validate_admin_login(request.form['password'])):
            return redirect(url_for('navigation_admin_page'))
        else:
            return render_template("login_admin.html"), 401
    else:
        return render_template("login_admin.html")
    
@app.route("/admin/navigation", methods=["GET"])
@admin_permission.require(http_exception=401)
@login_required
def navigation_admin_page():
    return render_template("navigation_admin.html")



#JobTaker jobmarket
@app.route("/jobtaker/jobmarket", methods=["GET"])
@jobtaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobtaker_page():
    return render_template("take_job.html")

@app.route("/jobtaker/jobmarket/confirm", methods=["POST"])
@jobtaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobtaker_confirm():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("take_job.html")
    if search == None:
        print("bad id")
        return render_template("take_job.html")
    (db_session, query) = search
    match JobState(int(request.form['state'])):
        case JobState.ACCEPTED_TAKER:
            try:
                query.first().progress_job_state(JobState(int(request.form['state'])), jobtaker_id=current_user.id, db_session=db_session)
            except ValueError as e:
                print(e)
                return render_template("take_job.html")
        case JobState.STARTED:
            try:
                query.first().progress_job_state(JobState(int(request.form['state'])), db_session=db_session)
            except ValueError as e:
                print(e)
                return render_template("take_job.html")
        case JobState.ENDED:
            try:
                query.first().progress_job_state(JobState(int(request.form['state'])), rating=int(request.form['rating']), db_session=db_session)
            except ValueError as e:
                print(e)
                return render_template("take_job.html")
        case _:
            print("cant do dat")
            return render_template("take_job.html")
    return render_template("take_job.html")

@app.route("/jobtaker/jobmarket/unconfirm", methods=["POST"])
@jobtaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobtaker_unconfirm():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("take_job.html")
    if search == None:
        print("bad id")
        return render_template("take_job.html")
    (db_session, query) = search
    query.first().deny_jobtaker_job_state(db_session)
    return render_template("take_job.html")




#JobMaker jobmarket
@app.route("/jobmaker/jobmarket", methods=["GET"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_page():
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/create", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_create():
    jobs.create_job(current_user, request)
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/confirm", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_confirm():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("make_job.html")
    if search == None:
        print("bad id")
        return render_template("make_job.html")
    (db_session, query) = search
    match JobState(int(request.form['state'])):
        case JobState.ACCEPTED_MAKER:
            try:
                query.first().progress_job_state(JobState(int(request.form['state'])), db_session=db_session)
            except ValueError as e:
                print(e)
                return render_template("make_job.html")
        case JobState.PAYED:
            try:
                query.first().progress_job_state(JobState(int(request.form['state'])), rating=int(request.form['rating']), db_session=db_session)
            except ValueError as e:
                print(e)
                return render_template("make_job.html")
        case _:
            print("cant do dat")
            return render_template("make_job.html")
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/edit", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_edit():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("make_job.html")
    if search == None:
        print("bad id")
        return render_template("make_job.html")
    (db_session, query) = search
    query.first().edit_job(request, db_session)
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/deny_jobtaker", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_deny_jobtaker():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("make_job.html")
    if search == None:
        print("bad id")
        return render_template("make_job.html")
    (db_session, query) = search
    query.first().deny_jobtaker_job_state(db_session)
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/delete", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_delete_job():
    try:
        search = jobs.get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("make_job.html")
    if search == None:
        print("bad id")
        return render_template("make_job.html")
    (db_session, query) = search
    query.first().delete_job(db_session)
    return render_template("make_job.html")


@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for("index_page"))

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    user_on_identity_loaded(sender, identity)
    
if __name__ == "__main__":
    app.run(debug=True)