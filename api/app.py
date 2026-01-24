#Imports
import global_objects as global_objects
from datetime import datetime, timezone
from enum import Enum

import passwords
import users
import jobs
from global_objects import db, login_manager, admin_permission, jobtaker_permission, jobmaker_permission, JobState
from flask import Flask, flash, render_template, redirect, request, session, url_for
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import CountryType, Country
from flask_login import current_user, login_required, logout_user
from flask_principal import identity_changed, AnonymousIdentity, identity_loaded
from jobs import Job

#main app file

#App
app = Flask(__name__)

app.secret_key = "epstein grape chiggers"#todo:move into cfg file

login_manager.init_app(app)

#Db setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_BINDS"] = {
    "jobtakers": "sqlite:///users.db",
    "jobmakers": "sqlite:///users.db",
    "jobtaker_passwords": "sqlite:///passwords.db",
    "jobmaker_passwords": "sqlite:///passwords.db",
    "jobs": "sqlite:///jobs.db",
    "logs": "sqlite:///logs.db"
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

#initialize all of the modules
users.init_module(app)
passwords.init_module(app)
jobs.init_module(app)
global_objects.setup_principals(app)
    
class Log(db.Model):
    __bind_key__ = "logs"
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
    db_session = sessionmaker(bind=db.engines['logs'])()
    db_session.begin()
    if db_session.query(Log).filter(Log.sender_id == 1).count() == 0 or force:
        db_session.add(Log(1, -1, datetime.min, "i will do something brand safe to u"))
    db_session.commit()
    
with app.app_context():
    db.create_all(bind_key=["jobtakers","jobmakers","jobtaker_passwords","jobmaker_passwords","jobs","logs"])
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
    session['account_type'] = ""
    return redirect(url_for("index_page"))

@app.route('/delete', methods=["GET"])
@login_required
def delete():
    user = current_user
    session_type = session['account_type']
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(app, identity=AnonymousIdentity())
    session['account_type'] = ""
    users.delete_account(user, session_type)
    return redirect(url_for("index_page"))



#JobTaker account management
@app.route("/login/jobtaker", methods=["GET", "POST"])
def login_jobtaker():
    if(request.method == "POST"):
        if(users.validate_login_attempt(request, True)):
            return redirect(url_for('jobmarket_jobtaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobtaker.html"), 401
    else:
        return render_template("login_jobtaker.html")

@app.route("/edit/jobtaker", methods=["GET", "POST"])
@jobtaker_permission.require(http_exception=401)
@login_required
def edit_account_jobtaker():
    if(request.method == "POST"):
        if(users.edit_account(current_user, request, True)):
            return redirect(url_for('protected_jobtaker_page'))
        else:
            flash("looser", "error")
            return render_template("edit_jobtaker.html"), 401
    else:
        return render_template("edit_jobtaker.html")
    
@app.route("/create/jobtaker", methods=["GET", "POST"])
def create_account_jobtaker():
    if(request.method == "POST"):
        if(users.create_account(request, True)):
            return redirect(url_for("login_jobtaker"))
        else:
            return redirect(url_for("create_account_jobtaker")), 401
    else:
        return render_template("create_jobtaker.html")



#JobMaker account management
@app.route("/login/jobmaker", methods=["GET", "POST"])
def login_jobmaker():
    if(request.method == "POST"):
        if(users.validate_login_attempt(request, False)):
            return redirect(url_for('jobmarket_jobmaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobmaker.html"), 401
    else:
        return render_template("login_jobmaker.html")
    
@app.route("/edit/jobmaker", methods=["GET", "POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def edit_account_jobmaker():
    if(request.method == "POST"):
        if(users.edit_account(current_user, request, False)):
            return redirect(url_for('protected_jobmaker_page'))
        else:
            flash("looser", "error")
            return render_template("edit_jobmaker.html"), 401
    else:
        return render_template("edit_jobmaker.html")

@app.route("/create/jobmaker", methods=["GET", "POST"])
def create_account_jobmaker():
    if(request.method == "POST"):
        if(users.create_account(request, False)):
            return redirect(url_for("login_jobmaker"))
        else:
            return redirect(url_for("create_account_jobmaker")), 401
    else:
        return render_template("create_jobmaker.html")



#Admin view
@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if(request.method == "POST"):
        if(users.validate_admin_login(request.form['password'])):
            return redirect(url_for('navigation_admin_page'))
        else:
            return render_template("login_admin.html"), 401
    else:
        return render_template("login_admin.html")
    
@app.route("/navigation/admin", methods=["GET"])
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

@app.route("/jobtaker/confirm", methods=["POST"])
@jobtaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobtaker_confirm():
    jobs.update_job_state(int(request.form['job_id']), JobState(int(request.form['state'])))
    return render_template("take_job.html")



#JobMaker jobmarket
@app.route("/jobmaker/jobmarket", methods=["GET"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_page():
    return render_template("make_job.html")

@app.route("/jobmaker/create", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_create():
    jobs.create_job(current_user, request)
    return render_template("make_job.html")

@app.route("/jobmaker/confirm", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_confirm():
    jobs.update_job_state(int(request.form['job_id']), JobState(int(request.form['state'])))
    return render_template("make_job.html")

@app.route("/jobmaker/edit", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_edit():
    jobs.edit_job(current_user, request)
    return render_template("make_job.html")



@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for("index_page"))

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    users.on_identity_loaded(sender, identity)
    
if __name__ == "__main__":
    app.run(debug=True)