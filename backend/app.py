#Imports
from datetime import datetime, timezone
import sys
from atexit import register as register_atexit
import global_objects

from passwords import (init_module as password_init_module)
from users import (init_module as user_init_module,
                   verify_login_attempt as user_verify_login_attempt,
                   register_user_account,
                   verify_admin_login_attempt as user_verify_admin_login,
                   delete_unconfirmed_users,
                   confirm_user_account,
                   send_confirmation_email as user_send_confirmation_email)
from jobs import (init_module as job_init_module,
                  create_job,
                  get_job_by_id)
from global_objects import (db,
                            login_manager,
                            admin_permission,
                            jobtaker_permission,
                            jobmaker_permission,
                            JobState,
                            init_module as global_objects_init_module)
from flask import Flask, flash, render_template, redirect, request, session, url_for
from sqlalchemy.orm import sessionmaker
from flask_login import current_user, login_required, logout_user
from apscheduler.schedulers.background import BackgroundScheduler as BGScheduler
from flask_principal import identity_changed, AnonymousIdentity

#main app file

#App
app = Flask(__name__)

app.config.from_pyfile('./flask_config.py')
global_objects.testing = sys.argv[1] == "Test" if 1 < len(sys.argv) else False
if global_objects.testing : #you can now decide what templates the app uses based on if y run it /w Test as the first arg
    app.template_folder = '../test_html'
else:
    app.template_folder = '../app/'

#Scheduler
scheduler = BGScheduler(daemon=True)
scheduler.add_job(func=delete_unconfirmed_users, trigger='interval', hours=2)
scheduler.start()
register_atexit(scheduler.shutdown)

@app.before_request
def session_permanence_handler():
    #Makes the session impermanet if an admin acc is logged in
    session.permanent = session.get('account_type') != global_objects.ADMIN_SESSION_NAME

login_manager.init_app(app)

#Db setup
db.init_app(app)

#initialize all of the modules
global_objects_init_module(app)
user_init_module(app)
password_init_module(app)
job_init_module(app)
    
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

@app.route('/resend', methods=["GET"])
@login_required
def resend():
    user = current_user
    print(user_send_confirmation_email(user.id, user.__bind_key__ == global_objects.JOBTAKERS_BINDKEY))
    return redirect(url_for("index_page"))

@app.route('/confirm/<token>', methods=["GET"])
def confirm_account(token):
    result = confirm_user_account(token)
    if isinstance(result, int):
        print(f"code '{result}' while confirming")
        return f"Invalid or expired link. ({result})", 400
    (_, is_jobtaker) = result
    refresh_arg = {"Refresh" : f"3, url={ url_for(f'login_{'jobtaker' if is_jobtaker else 'jobmaker'}')}"}
    return "Email verified successfully!", refresh_arg


#JobTaker account management
@app.route("/jobtaker/login", methods=["GET", "POST"])
def login_jobtaker():
    if(request.method == "POST"):
        if(user_verify_login_attempt(request, True)):
            return redirect(url_for('jobmarket_jobtaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobtaker.html"), 404
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
            return render_template("edit_jobtaker.html"), 404
    else:
        return render_template("edit_jobtaker.html")
    
@app.route("/jobtaker/create", methods=["GET", "POST"])
def create_account_jobtaker():
    if(request.method == "POST"):
        if(register_user_account(request, True)):
            return redirect(url_for("login_jobtaker"))
        else:
            return redirect(url_for("create_account_jobtaker")), 404
    else:
        return render_template("create_jobtaker.html")



#JobMaker account management
@app.route("/jobmaker/login", methods=["GET", "POST"])
def login_jobmaker():
    if(request.method == "POST"):
        if(user_verify_login_attempt(request, False)):
            return redirect(url_for('jobmarket_jobmaker_page'))
        else:
            flash("looser", "error")
            return render_template("login_jobmaker.html"), 404
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
            return render_template("edit_jobmaker.html"), 404
    else:
        return render_template("edit_jobmaker.html")

@app.route("/jobmaker/create", methods=["GET", "POST"])
def create_account_jobmaker():
    if(request.method == "POST"):
        if(register_user_account(request, False)):
            return redirect(url_for("login_jobmaker"))
        else:
            return redirect(url_for("create_account_jobmaker")), 404
    else:
        return render_template("create_jobmaker.html")



#Admin view
@app.route("/admin/login", methods=["GET", "POST"])
def login_admin():
    if(request.method == "POST"):
        if(user_verify_admin_login(request.form['password'])):
            return redirect(url_for('navigation_admin_page'))
        else:
            return render_template("login_admin.html"), 404
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
        search = get_job_by_id(int(request.form['job_id']))
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
        search = get_job_by_id(int(request.form['job_id']))
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
    create_job(current_user, request)
    return render_template("make_job.html")

@app.route("/jobmaker/jobmarket/confirm", methods=["POST"])
@jobmaker_permission.require(http_exception=401)
@login_required
def jobmarket_jobmaker_confirm():
    try:
        search = get_job_by_id(int(request.form['job_id']))
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
        search = get_job_by_id(int(request.form['job_id']))
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
        search = get_job_by_id(int(request.form['job_id']))
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
        search = get_job_by_id(int(request.form['job_id']))
    except ValueError as e:
        print(e)
        return render_template("make_job.html")
    if search == None:
        print("bad id")
        return render_template("make_job.html")
    (db_session, query) = search
    query.first().delete_job(db_session)
    return render_template("make_job.html")
    
#Error handlers
@login_manager.unauthorized_handler #User can both lack perms or not be logged in, so we check for both
def unauthorized_handler(e):
    return Unathorized(e)

@app.errorhandler(401)
def Unathorized(e):
    print(e)
    return "Not Authorized ya dingus" #Todo:put a actual page here

@app.errorhandler(404)
def Not_Found(e):
    print(e)
    return "Didn found that" #Todo:put a actual page here
    
if __name__ == "__main__":
    app.run(debug=True)