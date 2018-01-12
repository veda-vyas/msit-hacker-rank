from flask import Flask, flash, redirect, render_template, \
     request, jsonify, url_for, session, send_from_directory, \
     make_response, Response as ress, send_file
from datetime import datetime, timedelta, date
import time
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from flask.ext.login import LoginManager, login_required, login_user, \
    logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session
from requests.exceptions import HTTPError
from config import BaseConfig
import StringIO
import csv
import re
import mimetypes
import pytz
from werkzeug.utils import secure_filename
import zipfile
from sqlalchemy import cast, Date, extract
from functools import wraps
# from seccomp import SecureEvalHost
# import timestring

IST = pytz.timezone('Asia/Kolkata')
root = os.path.join(os.path.dirname(os.path.abspath(__file__)))

class Auth:
    CLIENT_ID = ('891614416155-5t5babc77fivqfslma1c3u6r2r9fp1o1.apps.googleusercontent.com')
    CLIENT_SECRET = 'UnGr0t5VT0d3l4PLgICkQoy6'
    REDIRECT_URI = 'https://127.0.0.1:5000/oauth2callback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email']

class Config:
    APP_NAME = "MSIT Course Page"
    SECRET_KEY = "somethingsecret"

# class DevConfig(Config):
#     DEBUG = True
#     SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:veda1997@localhost/module_page'

# config = {
#     "dev": DevConfig,
#     "default": DevConfig
# }

app = Flask(__name__)

app.debug_log_format = "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s"
log_path = os.path.join(os.getcwd(),'logs.log')
log_path = 'logs.log'
logHandler = RotatingFileHandler(log_path, maxBytes=10000, backupCount=1)
logHandler.setLevel(logging.NOTSET)
app.logger.addHandler(logHandler)
app.logger.setLevel(logging.NOTSET)
login_log = app.logger
app.debug = True
app.secret_key = "some_secret"
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"
ADMINS = ['vedavyas.yeleswarapu@gmail.com']

#from werkzeug.serving import make_ssl_devcert
#make_ssl_devcert('./ssl', host='localhost')

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    tokens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(IST))

class Test(db.Model):
    __tablename__ = "test"
    id = db.Column(db.Integer, primary_key=True)
    identity = db.Column(db.String(5), unique=True)
    name = db.Column(db.Text)
    no_of_questions = db.Column(db.Integer)
    start = db.Column(db.DateTime, default=datetime.now(IST))
    end = db.Column(db.DateTime, default=datetime.now(IST))
    duration = db.Column(db.Integer, default=120)
    description = db.Column(db.Text, default="")
    instructions = db.Column(db.Text, default="")
    grading = db.Column(db.Text, default="")

class Question(db.Model):
    __tablename__ = "question"
    id = db.Column(db.Integer, primary_key=True)
    identity = db.Column(db.String(10), unique=True)
    testid = db.Column(db.String(5))
    name = db.Column(db.Text)
    statement = db.Column(db.Text)
    input_format = db.Column(db.Text)
    output_format = db.Column(db.Text)
    constraints = db.Column(db.Text)
    marks = db.Column(db.Integer)
    languages = db.Column(db.Text, default="Python")

class Activity(db.Model):
    __tablename__ = "activity"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    name = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now(IST))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session['email'] not in ADMINS:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        app.logger.info(e)
        return render_template('error.html')

@app.route('/admin')
@login_required
@admin_login_required
def admin():
    try:
        return render_template('admin.html')
    except Exception as e:
        app.logger.info(e)
        return render_template('error.html')

@app.route('/load_tests', methods=['POST'])
@login_required
@admin_login_required
def load_tests():
    try:
        # tests = Test.query.filter(Test.name=="xyz").all()
        tests = Test.query.all()
        tests_arr = []
        for test in tests:
            tests_arr.append([
                "<a href='/edit_test/"+test.identity+"'>"+test.identity+"</a>", test.name, test.no_of_questions, test.start.strftime("%d-%m-%Y %H:%M"), test.end.strftime("%d-%m-%Y %H:%M"), test.duration 
            ])
        return json.dumps(tests_arr)
    except Exception as e:
        app.logger.info("Error in load_tests: "+str(e))
        return render_template('error.html')

@app.route('/load_questions/<testid>', methods=['POST'])
@login_required
@admin_login_required
def load_questions(testid=None):
    if testid == None:
        app.logger.info("requested load_questions without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        try:
            # tests = Test.query.filter(Test.name=="xyz").all()
            questions = Question.query.filter(Question.testid==testid).all()
            questions_arr = []
            for question in questions:
                questions_arr.append([
                    "<a href='/edit_question/"+question.testid+"/"+question.identity+"'>"+question.identity+"</a>", question.name, question.languages, question.marks
                ])
            return json.dumps(questions_arr)
        except Exception as e:
            app.logger.info("Error in load_questions: "+str(e))
            return render_template('error.html')

@app.route('/create_test', methods=['GET','POST'])
@login_required
@admin_login_required
def create_test(message=None, valid=None):
    if request.method == "GET":
        try:
            return render_template("create_test.html", message=message, valid=valid)
        except Exception as e:
            app.logger.info("Error in create_test: "+str(e))
            return render_template('error.html')
    if request.method == "POST":
        try:
            f = request.form
            name = f["name"]
            id = f["id"]
            start = datetime.strptime(f["start"], "%d-%m-%Y %H:%M")
            end = datetime.strptime(f["end"], "%d-%m-%Y %H:%M")
            no_of_questions = f["no_of_questions"]
            duration = f["duration"]
            tests = Test.query.filter(Test.identity==id).all()
            if len(tests) == 0:
                if len(id) <= 5:
                    new_test = Test(identity=id,name=name,no_of_questions=no_of_questions,start=start,end=end,duration=duration)
                    db.session.add(new_test)
                    db.session.commit()
                    message = "Successfully created the test."
                    valid = True
                    return redirect(url_for("admin"))
                else:
                    message = "Please choose a TestID which is <=5 characters"
                    valid = False    
                    return redirect(url_for("create_test", message=message, valid=valid))
            else:
                existing_test = tests[0]

                existing_test.identity = id 
                existing_test.name = name 
                existing_test.no_of_questions = no_of_questions 
                existing_test.start = start 
                existing_test.end = end 
                existing_test.duration = duration 
                db.session.commit()
                
                message = "Test ID already exists. Existing Test ("+id+") updated."
                valid = True

                return redirect(url_for("edit_test", testid=id, message=message, valid=valid))
        except Exception as e:
            app.logger.info("Error in create_test: "+str(e))
            return redirect(url_for("create_test", message=str(e), valid=False))

@app.route('/create_question/<testid>', methods=['GET','POST'])
@login_required
@admin_login_required
def create_question(testid=None, message=None, valid=None):
    if testid == None:
        app.logger.info("requested create_question without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        if request.method == "GET":
            try:
                return render_template("create_question.html", testid=testid, message=message, valid=valid)
            except Exception as e:
                app.logger.info("Error in create_question: "+str(e))
                return render_template('error.html')
        if request.method == "POST":
            try:
                f = request.form
                name = f["name"]
                id = f["id"]
                statement = ""
                input_format = ""
                output_format= ""
                constraints = ""
                marks = f['marks']
                questions = Question.query.filter(Question.identity==id,Question.testid==testid).all()
                if len(questions) == 0:
                    if len(id) <= 10:
                        new_question = Question(identity=id,testid=testid,name=name,statement=statement,input_format=input_format,output_format=output_format,constraints=constraints,marks=marks)
                        db.session.add(new_question)
                        db.session.commit()
                        message = "Successfully created a question."
                        valid = True
                    else:
                        message = "Please choose a QuestionID which is <=10 characters"
                        valid = False    
                    return redirect(url_for("create_question", testid=testid, message=message, valid=valid))
                else:
                    existing_question = questions[0]

                    existing_question.identity = id
                    existing_question.name = name
                    existing_question.statement = statement
                    existing_question.input_format = input_format 
                    existing_question.output_format = output_format 
                    existing_question.constraints = constraints 
                    existing_question.marks = marks 
                    db.session.commit()
                    
                    message = "Question ID already exists. Existing Question ("+id+") updated."
                    valid = True

                    return redirect(url_for("create_question", testid=testid, message=message, valid=valid))
            except Exception as e:
                app.logger.info("Error in create_question: "+str(e))
                return redirect(url_for("create_question", message=str(e), valid=False))

@app.route('/edit_test/<testid>', methods=['GET'])
@login_required
@admin_login_required
def edit_test(testid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_test without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        test = Test.query.filter(Test.identity==testid).first() 
        if test:
            return render_template("edit_test.html", identity=test.identity, name=test.name, no_of_questions=test.no_of_questions, start=test.start.strftime("%d-%m-%Y %H:%M"), end=test.end.strftime("%d-%m-%Y %H:%M"), duration=test.duration, message=message, valid=valid)
        else:   
            return redirect(url_for("create_test"))

@app.route('/edit_question/<testid>/<qid>', methods=['GET'])
@login_required
@admin_login_required
def edit_question(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_question without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested edit_question without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.testid==testid,Question.identity==qid).first() 
        if question:
            return render_template("edit_question.html", identity=question.identity, testid=question.testid, name=question.name, statement=question.statement, input_format=question.input_format, output_format=question.output_format, constraints=question.constraints, marks=question.marks, message=message, valid=valid)
        else:   
            return redirect(url_for("create_question", testid=testid))

@app.route('/edit_description/<testid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_description(testid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_description without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        test = Test.query.filter(Test.identity==testid).first()
        if test:
            if request.method == 'GET':
                return test.description
            if request.method == 'POST':
                test.description = request.form['description']
                db.session.commit()
                message = "Updated description."
                valid = True
                return redirect(url_for("edit_test", testid=test.identity , identity=test.identity, name=test.name, no_of_questions=test.no_of_questions, start=test.start.strftime("%d-%m-%Y %H:%M"), end=test.end.strftime("%d-%m-%Y %H:%M"), duration=test.duration, message=message, valid=valid))
        else:   
            return redirect(url_for("create_test"))

@app.route('/edit_grading/<testid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_grading(testid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_grading without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        test = Test.query.filter(Test.identity==testid).first()
        if test:
            if request.method == 'GET':
                return test.grading
            if request.method == 'POST':
                test.grading = request.form['grading']
                db.session.commit()
                message = "Updated grading."
                valid = True
                return redirect(url_for("edit_test", testid=test.identity , identity=test.identity, name=test.name, no_of_questions=test.no_of_questions, start=test.start.strftime("%d-%m-%Y %H:%M"), end=test.end.strftime("%d-%m-%Y %H:%M"), duration=test.duration, message=message, valid=valid))
        else:   
            return redirect(url_for("create_test"))

@app.route('/edit_instructions/<testid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_instructions(testid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_instructions without TestID: "+str(e))
        return redirect(url_for('admin'))
    else:
        test = Test.query.filter(Test.identity==testid).first()
        if test:
            if request.method == 'GET':
                return test.instructions
            if request.method == 'POST':
                test.instructions = request.form['instructions']
                db.session.commit()
                message = "Updated instructions."
                valid = True
                return redirect(url_for("edit_test", testid=test.identity , identity=test.identity, name=test.name, no_of_questions=test.no_of_questions, start=test.start.strftime("%d-%m-%Y %H:%M"), end=test.end.strftime("%d-%m-%Y %H:%M"), duration=test.duration, message=message, valid=valid))
        else:   
            return redirect(url_for("create_test"))

@app.route('/edit_statement/<testid>/<qid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_statement(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_statement without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested edit_statement without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.identity==qid,Question.testid==testid).first()
        if question:
            if request.method == 'GET':
                app.logger.info("question statement"+question.statement)
                return question.statement
            if request.method == 'POST':
                app.logger.info("Question statement post: "+request.form['statement'])
                question.statement = request.form['statement']
                db.session.commit()
                app.logger.info("Question statement after dbcommit: "+question.statement)
                message = "Updated statement."
                valid = True
                return redirect(url_for("edit_question", testid=question.testid , qid=question.identity))
        else:   
            return redirect(url_for("create_question"))

@app.route('/edit_input_format/<testid>/<qid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_input_format(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_input_format without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested edit_input_format without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.identity==qid,Question.testid==testid).first()
        if question:
            if request.method == 'GET':
                # app.logger.info("question input_format"+question.input_format)
                return question.input_format
            if request.method == 'POST':
                # app.logger.info("Question input_format post: "+request.form['input_format'])
                question.input_format = request.form['input_format']
                db.session.commit()
                # app.logger.info("Question input_format after dbcommit: "+question.input_format)
                message = "Updated input_format."
                valid = True
                return redirect(url_for("edit_question", testid=question.testid , qid=question.identity))
        else:   
            return redirect(url_for("create_question"))

@app.route('/edit_output_format/<testid>/<qid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_output_format(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_output_format without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested edit_output_format without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.identity==qid,Question.testid==testid).first()
        if question:
            if request.method == 'GET':
                # app.logger.info("question output_format"+question.output_format)
                return question.output_format
            if request.method == 'POST':
                # app.logger.info("Question output_format post: "+request.form['output_format'])
                question.output_format = request.form['output_format']
                db.session.commit()
                # app.logger.info("Question output_format after dbcommit: "+question.output_format)
                message = "Updated output_format."
                valid = True
                return redirect(url_for("edit_question", testid=question.testid , qid=question.identity))
        else:   
            return redirect(url_for("create_question"))

@app.route('/edit_constraints/<testid>/<qid>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def edit_constraints(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested edit_constraints without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested edit_constraints without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.identity==qid,Question.testid==testid).first()
        if question:
            if request.method == 'GET':
                # app.logger.info("question constraints"+question.constraints)
                return question.constraints
            if request.method == 'POST':
                # app.logger.info("Question constraints post: "+request.form['constraints'])
                question.constraints = request.form['constraints']
                db.session.commit()
                # app.logger.info("Question constraints after dbcommit: "+question.constraints)
                message = "Updated constraints."
                valid = True
                return redirect(url_for("edit_question", testid=question.testid , qid=question.identity))
        else:   
            return redirect(url_for("create_question"))

@app.route('/get_content/<filename>', methods=['GET'])
@login_required
@admin_login_required
def get_content(filename):
    content = ""
    with open(filename, "rb") as f:
        content = f.read()
    return content


@app.route('/evalcode', methods=['POST'])
@login_required
@admin_login_required
def evalcode(execution_path,inputs,outputs,timeout):
    code =  get_content(execution_path)
    if code == "":
        return redirect(url_for(request.referrer))
    
    global results

    def execute(execution_path,input,output,timeout,index):
        # with app.test_request_context():
        import subprocess
        from threading import Timer
        from threading import Thread

        testcase_eval = execution_path.split("/")
        solution_file_path = testcase_eval[-2]+"/"+testcase_eval[-1]

        cmd = ["sandbox/bin/run", "python", solution_file_path]
        app.logger.info("cmd is: %s", cmd)
        p = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        timer = Timer(timeout, p.kill)
        timer.start()

        given_input=open(input,"rb").read()
        expected_output=open(output,"rb").read()
        your_output,err = p.communicate(given_input)
        your_output=str(your_output)
        
        if timer.is_alive():
            timer.cancel()

            your_output = your_output.replace('\r','').rstrip() #remove trailing newlines, if any
            expected_output = expected_output.replace('\r','').rstrip()

            if your_output == expected_output:
                out,err = "Testcase Passed.", ""
            elif err:
                out,err = your_output,err
            else:
                out,err = "","Input: "+given_input+" \nExpected: "+expected_output+" \nYour Output: "+your_output
            
            results[index]['output'] = out
            results[index]['error'] = err

        return True
    
    if request.method == "POST":
        if len(inputs) == len(outputs):
            from threading import Thread
            threads = []
            results = []
            for i in range(len(inputs)):
                results.append({})
                process = Thread(target=execute, args=[execution_path,inputs[i],outputs[i],5,i])
                process.start()
                threads.append(process)
            for process in threads:
                process.join()

            # if os.path.exists(execution_path):
            #     os.remove(execution_path)
            os.remove(execution_path)
            return results,""
        else:
            os.remove(execution_path)
            return "","Lenghts of Inputs and Outputs is not same."

@app.route('/getoutput/<testid>/<qid>', methods=['GET'])
@login_required
@admin_login_required
def getoutput(testid=None,qid=None):
    if testid == None:
        app.logger.info("requested getcode without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested getcode without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        if request.method == "GET":
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            tmp_path = 'submissions/'+session['email']+'/'+testid
            directory = os.path.join(BASE_DIR, tmp_path)
            
            if os.path.exists(directory+"/"+qid+".txt"):
                f = open(directory+"/"+qid+".txt", "r")
                content = f.read()
                app.logger.info("getting output: %s",content)
                return content

            return "Could not fetch the output. Execute code again."

@app.route('/getcode/<testid>/<qid>', methods=['GET'])
@login_required
@admin_login_required
def getcode(testid=None,qid=None):
    if testid == None:
        app.logger.info("requested getcode without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested getcode without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        if request.method == "GET":
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            tmp_path = 'submissions/'+session['email']+'/'+testid
            directory = os.path.join(BASE_DIR, tmp_path)
            
            if os.path.exists(directory+"/"+qid+".py"):
                f = open(directory+"/"+qid+".py", "r")
                return f.read()

            return "Could not fetch the code. Try submitting again."

@app.route('/gettestcases/<testid>/<qid>', methods=['POST'])
@login_required
@admin_login_required
def gettestcases(testid=None,qid=None):
    if testid == None:
        app.logger.info("requested gettestcases without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested gettestcases without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        if request.method == "POST":
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            tmp_path = 'testcases/'+testid+'/'+qid
            directory = os.path.join(BASE_DIR, tmp_path)
            
            inputs = []
            outputs = []
            
            if os.path.exists(directory):
                for root,dirs,files in os.walk(directory):
                    for file in files:
                        if 'input' in file and '.txt' in file:
                            inputs.append(directory+"/"+file)
                        if 'output' in file and '.txt' in file:
                            outputs.append(directory+"/"+file)
                    break

            inputs = sorted(inputs)
            outputs = sorted(outputs)
            
            return inputs,outputs

@app.route('/submitcode/<testid>/<qid>', methods=['POST'])
@login_required
@admin_login_required
def submitcode(testid=None, qid=None, message=None, valid=False):
    if testid == None:
        app.logger.info("requested submitcode without TestID: "+str(e))
        return redirect(url_for('admin'))
    if qid == None:
        app.logger.info("requested submitcode without QuestionID: "+str(e))
        return redirect(url_for('admin'))
    else:
        question = Question.query.filter(Question.identity==qid,Question.testid==testid).first()
        if question:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            tmp_path = 'submissions/'+session['email']+'/'+testid
            directory = os.path.join(BASE_DIR, tmp_path)

            if request.method == 'POST':
                code = request.form['code_'+qid]
                execution_path = os.path.join(BASE_DIR, 'sandbox/root/'+session['email'])
                

                if request.form["action"] == "Test Run":
                    app.logger.info("Test Running Code: %s",code)
                    if not os.path.exists(execution_path):
                        os.makedirs(execution_path)
                    execution_path+="/Solution.py"
                    inputs,outputs = gettestcases(testid, qid)
                    if not os.path.exists(execution_path):
                        with open(execution_path, "wb") as f:
                            f.write(code)
                        output,err = evalcode(execution_path, inputs, outputs, 5)
                    else:
                        output,err = "","An instance of your previous execution is still running. Please email <vy[at]fju[dot]us>."
                        
                if request.form["action"] == "Submit Solution":
                    app.logger.info("Submitting Code: %s",code)
                    if not os.path.exists(directory):
                        os.makedirs(directory)
                    with open(directory+"/"+qid+".py", "wb") as f:
                        f.write(code)
                    if not os.path.exists(execution_path):
                        os.makedirs(execution_path)
                    execution_path+="/Solution.py"
                    inputs,outputs = gettestcases(testid, qid)
                    if not os.path.exists(execution_path):
                        with open(execution_path, "wb") as f:
                            f.write(code)
                        output,err = evalcode(execution_path, inputs, outputs, 5)
                        output = json.dumps(output)
                    else:
                        output,err = "","An instance of your previous execution is still running. Please email <vy[at]fju[dot]us>."
                
                with open(directory+"/"+qid+"_output.json", "wb") as f:
                    if output == "":
                        f.write(err)
                    else:
                        f.write(output)
                
                return redirect(url_for("edit_question", testid=question.testid , qid=question.identity, error=err, output=output, show_editor=True))
        else:   
            return redirect(url_for("create_question"))

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/oauth2callback')
def callback():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    if 'code' not in request.args and 'oauth_state' not in request.args:
        return redirect(url_for('login'))
    else:
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except HTTPError:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User()
                user.email = email
            user.name = user_data['name']
            print(token)
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)

            activity = Activity()
            activity.email = email
            activity.name = "LOGIN"
            activity.timestamp = datetime.now(IST)
            db.session.add(activity)

            db.session.commit()
            login_user(user)
            session['email'] = email
            app.logger.info(session['email'])
            return redirect(url_for('index'))
    return 'Could not fetch your information.'

@app.route('/error')
@login_required
def error():
    return render_template('error.html')

@app.route('/logout')
@login_required
def logout():
    activity = Activity()
    activity.email = session['email']
    activity.name = "LOGOUT"
    activity.timestamp = datetime.now(IST)
    db.session.add(activity)

    db.session.commit()
    logout_user()
    return redirect(url_for('login'))

@app.route('/styles/<path:path>')
@login_required
def send_stylesheets(path):
    app.logger.info("seeking for %s from %s at %s"%(path, request.headers.get('X-Forwarded-For', request.remote_addr), datetime.now()))
    return send_from_directory(root+"/styles", path)

@app.route('/scripts/<path:path>')
@login_required
def send_javascripts(path):
    app.logger.info("seeking for %s from %s at %s"%(path, request.headers.get('X-Forwarded-For', request.remote_addr), datetime.now()))
    return send_from_directory(root+"/scripts", path)

@app.route('/send_heatmap_data/<path:path>')
@login_required
def send_heatmap_data(path):
    app.logger.info("seeking for %s from %s at %s"%(path, request.headers.get('X-Forwarded-For', request.remote_addr), datetime.now()))
    return send_from_directory(root+"/templates/heatmap/", path)

@app.route('/content/<path:path>')
@login_required
def send_content(path):
    #app.logger.info("seeking for %s from %s at %s"%(path, request.headers.get('X-Forwarded-For', request.remote_addr), datetime.now()))
    activity = Activity()
    activity.email = session['email']
    activity.name = "DOWNLOADED SUBMISSION - /content/"+path
    activity.timestamp = datetime.now(IST)
    db.session.add(activity)

    db.session.commit()

    return send_from_directory(root+"/content", path)

def get_students_activity():
        result = Activity.query.all()
        table = []
        for entry in result:
            activity = {}
            activity["email"] = entry.email
            activity["timestamp"] = entry.timestamp
            activity["activity"] = entry.name
            activity["question"] = ""
            activity["response"] = ""
            table.append(activity)
        questions = ActivityFormSubmissions.query.all()
        for question in questions:
            activity = {}
            activity["email"] = question.email
            activity["timestamp"] = question.timestamp
            activity["activity"] = question.name
            activity["question"] = question.question
            activity["response"] = question.response
            table.append(activity)
        return table

def get_students_activity_by_date(date):
        table = []
        questions = ActivityFormSubmissions.query.filter(ActivityFormSubmissions.timestamp <= date).all()
        for question in questions:
            activity = {}
            activity["email"] = question.email
            activity["timestamp"] = question.timestamp
            activity["activity"] = question.name
            activity["question"] = question.question
            activity["response"] = question.response
            table.append(activity)
        return table

def render_csv_from_student_activity(data):
        csvList = []
        header = [
                    "User",
                    "Timestamp",
                    "Activity",
                    "Question",
                    "Response"
                ]
        csvList.append(header)
        for csv_line in data:
            row = [csv_line["email"],
                    csv_line["timestamp"],
                    csv_line["activity"].encode("utf-8"),
                    csv_line["question"].encode("utf-8"),
                    csv_line["response"].encode("utf-8"),
                ]
            csvList.append(row)
        si = StringIO.StringIO()
        cw = csv.writer(si)
        cw.writerows(csvList)
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=StudentActivity.csv"
        output.headers["Content-type"] = "text/csv"
        return output

@app.route('/downloadSuperCSV')
@login_required
def downloadSuperCSV():
    if request.method == 'GET':
        activity = Activity()
        activity.email = session['email']
        activity.name = "DOWNLOAD STUDENT ACTIVITY"
        activity.timestamp = datetime.now(IST)
        db.session.add(activity)

        db.session.commit()

        data = get_students_activity()
    return render_csv_from_student_activity(data)

def prepare_dataset(data):
    csvreader = []
    for csv_line in data:
        row = [csv_line["email"],
                csv_line["timestamp"],
                csv_line["activity"],
                csv_line["question"],
                csv_line["response"]
            ]
        csvreader.append(row)
    return csvreader

def get_heatmap_data(input_data,output,modulenum):
    submission_count = 0

    critical_questions = {
        "MODULE1 ACTIVITY1":"1.1",
        "MODULE1 ACTIVITY2":"2.1",
        "MODULE1 ACTIVITY3":"3.1",
        "MODULE1 ACTIVITY4":"4.1",
        "MODULE1 ACTIVITY5":"5.2",
        "MODULE1 ACTIVITY6":"6.1",
        "MODULE1 ACTIVITY7":"7.2",
        "MODULE1 ACTIVITY8":"8.1",
        "MODULE1 ACTIVITY9":"9.1",
        "MODULE2 ACTIVITY1":"2.1.1",
        "MODULE2 ACTIVITY2":"2.2.1",
        "MODULE2 ACTIVITY3":"2.3.1",
        "MODULE2 ACTIVITY4":"2.4.1",
        "MODULE2 ACTIVITY5":"2.5.1",
        "MODULE2 ACTIVITY6":"2.6.1",
        "MODULE2 ACTIVITY7":"2.7.1",
        "MODULE2 ACTIVITY8":"2.8.1",
        "MODULE2 ACTIVITY9":"2.9.1",
        "MODULE2 ACTIVITY10":"2.10.1",
        "MODULE2 ACTIVITY11":"2.11.1",
        "MODULE2 ACTIVITY12":"2.12.1",
        "MODULE2 ACTIVITY13":"2.13.1",
        "MODULE2 ACTIVITY14":"2.14.1",
        "MODULE3 ACTIVITY1":"3.1.1",
        "MODULE3 ACTIVITY2":"3.2.1",
        "MODULE3 ACTIVITY3":"3.3.1",
        "MODULE3 ACTIVITY4":"3.4.2",
        "MODULE3 ACTIVITY5":"3.5.2",
        "MODULE3 ACTIVITY6":"3.6.1",
        "MODULE3 ACTIVITY7":"3.7.1",
        "MODULE3 ACTIVITY8":"3.8.1",
        "MODULE3 ACTIVITY9":"3.9.1",
        "MODULE4 ACTIVITY1":"4.1.1",
        "MODULE4 ACTIVITY2":"4.2.1",
        "MODULE4 ACTIVITY3":"4.3.1",
        "MODULE4 ACTIVITY4":"4.4.1",
        "MODULE4 ACTIVITY5":"4.5.1",
        "MODULE4 ACTIVITY6":"4.6.1",
        "MODULE4 ACTIVITY7":"4.7.1",
        "MODULE5 ACTIVITY1":"5.1.1",
        "MODULE5 ACTIVITY2":"5.2.1",
        "MODULE5 ACTIVITY3":"5.3.1",
        "MODULE5 ACTIVITY4":"5.4.1",
        "MODULE5 ACTIVITY5":"5.5.1",
        "MODULE5 ACTIVITY6":"5.6.1",
        "MODULE5 ACTIVITY7":"5.7.1",
        "MODULE5 ACTIVITY8":"5.8.1",
        "MODULE5 ACTIVITY9":"5.9.1",
        "MODULE5 ACTIVITY10":"5.10.1",
        "MODULE5 ACTIVITY11":"5.11.1",
        "MODULE6 ACTIVITY1":"6.1.1",
        "MODULE6 ACTIVITY2":"6.2.1",
        "MODULE6 ACTIVITY3":"6.3.1",
        "MODULE6 ACTIVITY4":"6.4.1",
        "MODULE6 ACTIVITY5":"6.5.1",
        "MODULE6 ACTIVITY6":"6.6.1",
        "MODULE6 ACTIVITY7":"6.7.1",
        "MODULE6 ACTIVITY8":"6.8.1",
        "MODULE6 ACTIVITY9":"6.9.1",
        "MODULE7 ACTIVITY1":"7.1.1",
        "MODULE7 ACTIVITY2":"7.2.1",
        "MODULE7 ACTIVITY3":"7.3.1",
        "MODULE7 ACTIVITY4":"7.4.1",
        "MODULE7 ACTIVITY5":"7.5.1",
        "MODULE7 ACTIVITY6":"7.6.1",
        "MODULE7 ACTIVITY7":"7.7.1",
        "MODULE7 ACTIVITY8":"7.8.1",
        "MODULE7 ACTIVITY9":"7.9.1",
        "MODULE7 ACTIVITY10":"7.10.1",
        "MODULE7 ACTIVITY11":"7.11.1",
        "MODULE7 ACTIVITY12":"7.12.1",
        "MODULE7 ACTIVITY13":"7.13.1",
        "MODULE7 ACTIVITY14":"7.14.1",
        "MODULE7 ACTIVITY15":"7.15.1"
    }

    activity_codes = {
        "MODULE1 ACTIVITY1 SUBMISSION":"1",
        "MODULE1 ACTIVITY2 SUBMISSION":"2",
        "MODULE1 ACTIVITY3 SUBMISSION":"3",
        "MODULE1 ACTIVITY4 SUBMISSION":"4",
        "MODULE1 ACTIVITY5 SUBMISSION":"5",
        "MODULE1 ACTIVITY6 SUBMISSION":"6",
        "MODULE1 ACTIVITY7 SUBMISSION":"7",
        "MODULE1 ACTIVITY8 FILE SUBMISSION":"8",
        "MODULE1 ACTIVITY8 FILE UBMISSION":"8",
        "MODULE1 ACTIVITY8 SUBMISSION":"8",
        "MODULE1 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE1 ACTIVITY9 SUBMISSION":"9",
        "MODULE1 ACTIVITY9 FILE UBMISSION":"9",
        "MODULE2 ACTIVITY1 SUBMISSION":"1",
        "MODULE2 ACTIVITY2 SUBMISSION":"2",
        "MODULE2 ACTIVITY3 SUBMISSION":"3",
        "MODULE2 ACTIVITY4 SUBMISSION":"4",
        "MODULE2 ACTIVITY5 SUBMISSION":"5",
        "MODULE2 ACTIVITY6 SUBMISSION":"6",
        "MODULE2 ACTIVITY7 SUBMISSION":"7",
        "MODULE2 ACTIVITY8 FILE SUBMISSION":"8",
        "MODULE2 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE2 ACTIVITY10 FILE SUBMISSION":"10",
        "MODULE2 ACTIVITY11 FILE SUBMISSION":"11",
        "MODULE2 ACTIVITY12 FILE SUBMISSION":"12",
        "MODULE2 ACTIVITY13 FILE SUBMISSION":"13",
        "MODULE2 ACTIVITY14 FILE SUBMISSION":"14",
        "MODULE3 ACTIVITY1 SUBMISSION":"1",
        "MODULE3 ACTIVITY2 SUBMISSION":"2",
        "MODULE3 ACTIVITY3 SUBMISSION":"3",
        "MODULE3 ACTIVITY4 SUBMISSION":"4",
        "MODULE3 ACTIVITY5 SUBMISSION":"5",
        "MODULE3 ACTIVITY6 FILE SUBMISSION":"6",
        "MODULE3 ACTIVITY7 FILE SUBMISSION":"7",
        "MODULE3 ACTIVITY8 FILE SUBMISSION":"8",
        "MODULE3 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE4 ACTIVITY1 SUBMISSION":"1",
        "MODULE4 ACTIVITY2 SUBMISSION":"2",
        "MODULE4 ACTIVITY3 SUBMISSION":"3",
        "MODULE4 ACTIVITY4 SUBMISSION":"4",
        "MODULE4 ACTIVITY5 SUBMISSION":"5",
        "MODULE4 ACTIVITY6 FILE SUBMISSION":"6",
        "MODULE4 ACTIVITY7 FILE SUBMISSION":"7",
        "MODULE5 ACTIVITY1 SUBMISSION":"1",
        "MODULE5 ACTIVITY2 SUBMISSION":"2",
        "MODULE5 ACTIVITY3 SUBMISSION":"3",
        "MODULE5 ACTIVITY4 SUBMISSION":"4",
        "MODULE5 ACTIVITY5 SUBMISSION":"5",
        "MODULE5 ACTIVITY6 SUBMISSION":"6",
        "MODULE5 ACTIVITY7 SUBMISSION":"7",
        "MODULE5 ACTIVITY8 SUBMISSION":"8",
        "MODULE5 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE5 ACTIVITY10 FILE SUBMISSION":"10",
        "MODULE5 ACTIVITY11 FILE SUBMISSION":"11",
        "MODULE6 ACTIVITY1 SUBMISSION":"1",
        "MODULE6 ACTIVITY2 SUBMISSION":"2",
        "MODULE6 ACTIVITY3 SUBMISSION":"3",
        "MODULE6 ACTIVITY4 SUBMISSION":"4",
        "MODULE6 ACTIVITY5 FILE SUBMISSION":"5",
        "MODULE6 ACTIVITY6 FILE SUBMISSION":"6",
        "MODULE6 ACTIVITY7 FILE SUBMISSION":"7",
        "MODULE6 ACTIVITY8 FILE SUBMISSION":"8",
        "MODULE6 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE7 ACTIVITY1 SUBMISSION":"1",
        "MODULE7 ACTIVITY2 SUBMISSION":"2",
        "MODULE7 ACTIVITY3 SUBMISSION":"3",
        "MODULE7 ACTIVITY4 SUBMISSION":"4",
        "MODULE7 ACTIVITY5 SUBMISSION":"5",
        "MODULE7 ACTIVITY6 SUBMISSION":"6",
        "MODULE7 ACTIVITY7 SUBMISSION":"7",
        "MODULE7 ACTIVITY8 FILE SUBMISSION":"8",
        "MODULE7 ACTIVITY9 FILE SUBMISSION":"9",
        "MODULE7 ACTIVITY10 FILE SUBMISSION":"10",
        "MODULE7 ACTIVITY11 FILE SUBMISSION":"11",
        "MODULE7 ACTIVITY12 FILE SUBMISSION":"12",
        "MODULE7 ACTIVITY13 FILE SUBMISSION":"13",
        "MODULE7 ACTIVITY14 FILE SUBMISSION":"14",
        "MODULE7 ACTIVITY15 FILE SUBMISSION":"15"
    }

    ignore_emails = ['vy@fju.us','sirimala.sreenath@gmail.com','vedavyas.yeleswarapu@gmail.com','pg@fju.us', "neeraj.sharma15@msitprogram.net", "deepakbhimavarapu@gmail.com", "murthyvemuri@msitprogram.net", "manasa_a@msitprogram.net", "k.rajeshkumar@msitprogram.net", "rehana@msitprogram.net", "sivashankar@msitprogram.net"]

    submissions = {}

    activities_list = []

    hours = [9,10,11,12,13,14,15,16,17,18]

    with open(output, 'wb') as csvfile2:

        csvreader = prepare_dataset(input_data)

        for row in csvreader:
            if modulenum not in row[2]:
                app.logger.info(modulenum)
                continue

            localized_datetime = row[1].replace(tzinfo=pytz.utc).astimezone(IST)

            if row[2] not in activity_codes:
                continue

            for hour in hours:
                if (activity_codes[row[2]],hour*60+20) not in submissions:
                    submissions[(activity_codes[row[2]],hour*60+20)] = 0
                if (activity_codes[row[2]],hour*60+40) not in submissions:
                    submissions[(activity_codes[row[2]],hour*60+40)] = 0
                if (activity_codes[row[2]],hour*60+60) not in submissions:
                    submissions[(activity_codes[row[2]],hour*60+60)] = 0

            if (activity_codes[row[2]],19*60) not in submissions:
                submissions[(activity_codes[row[2]],19*60)] = 0

            if row[0] not in ignore_emails and row[2] in activity_codes:

                if int(activity_codes[row[2]]) not in activities_list:
                    activities_list.append(int(activity_codes[row[2]]))

                if "UBMISSION" in row[2] and "DOWNLOADED" not in row[2] and row[3] != '':
                    if critical_questions[row[2].split(' ')[0]+' '+row[2].split(' ')[1]] in row[3].split(' ')[0]:
                        submission_count+=1
                        hour = localized_datetime.hour
                        minute = localized_datetime.minute
                        if hour in hours:
                            if minute in range(20):
                                submissions[(activity_codes[row[2]],hour*60+20)] += 1
                            if minute in range(20,40):
                                submissions[(activity_codes[row[2]],hour*60+40)] += 1
                            if minute in range(40,60):
                                submissions[(activity_codes[row[2]],hour*60+60)] += 1
                        else:
                            if (activity_codes[row[2]],19*60) in submissions:
                                submissions[(activity_codes[row[2]],19*60)] += 1

        sorted_submissions = sorted(submissions, key=lambda element: (element[0], element[1]))

        #write cumulative data to csv
        current_activity = ""
        current_value = 0
        # csvlist = []
        csvfile2.write("day\thour\tvalue\n")
        prev_entry = 0
        for entry in sorted_submissions:
            if prev_entry == entry[0]:
                prev_val += submissions[entry]
                csvfile2.write(str(entry[0])+"\t"+str((entry[1]-540)/20)+"\t"+str(prev_val)+"\n")
            else:
                prev_entry = entry[0]
                prev_val = submissions[entry]
                csvfile2.write(str(entry[0])+"\t"+str((entry[1]-540)/20)+"\t"+str(prev_val)+"\n")
            # csvlist.append([int(entry[0]),entry[1],int(submissions[entry])])
            # app.logger.info(csvlist)
        return activities_list

@app.route('/heatmap/<date>/<modulenum>')
@app.route('/heatmap')
@login_required
def heatmap(date="03-10-2017", modulenum="MODULE1"):
    if request.method == 'GET':
        day,month,year = date.split("-")
        filename = "data"+day+"-"+month+"-"+year+".tsv"
        activities_list = get_heatmap_data(get_students_activity_by_date(datetime(int(year),int(month),int(day)+1)),"/var/www/adsmodulepage/templates/heatmap/"+filename,modulenum)
        app.logger.info(activities_list)
        return render_template("heatmap/heatmap.html", heatmap_data=[date,sorted(activities_list)])

def send_file_partial(path):
    range_header = request.headers.get('Range', None)
    if not range_header: return send_file(path)

    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()

    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 + 1 - byte1

    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = ress(data,
        206,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))
    return rv

@app.route('/play/<path:song>')
def play(song):
    return send_file_partial(root+"/"+song)

@app.route('/playvideo/<path:song>')
@login_required
def playvideo(song):
    activity = Activity()
    activity.email = session['email']
    activity.name = "WATCHED VIDEO: "+song
    activity.timestamp = datetime.now(IST)
    db.session.add(activity)

    db.session.commit()
    return '<video id="video" controls type="video/mp4" width="100%" src="/play/'+song+'" preload="auto" autoplay>Your browser does not support the video tag.</video>'

# ActivityFormSubmissions_email_index.create(bind=db)
# assert ActivityFormSubmissions_email_index in ActivityFormSubmissions.__table__.indexes
# assert ActivityFormSubmissions.__table__.c.name not in set(ActivityFormSubmissions_email_index.columns)
# assert ActivityFormSubmissions.__table__.c.email in set(ActivityFormSubmissions_email_index.columns)
db.create_all()

if __name__ == "__main__":
        # from werkzeug.serving import make_ssl_devcert
        # make_ssl_devcert('./ssl', host='localhost')
        app.debug = True
        app.run(ssl_context=('ssl.crt','ssl.key'))
