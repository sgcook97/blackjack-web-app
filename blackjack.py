from flask import Flask, render_template, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import random
from dotenv import load_dotenv, find_dotenv
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin


load_dotenv(find_dotenv())
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_TYPE"] = "filesystem"


@login_manager.user_loader
def load_user(user_id):
    return Person.query.get(int(user_id))

#########################################################################

# creates a table of users
class Person(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"Person with username: {self.username}"

    def __init__(self, username):
        self.username = username


# create tables
with app.app_context():
    db.create_all()

#########################################################################


# MAIN PAGE
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


# verifies if a user is valid or not
def validateUser(username):
    valid = db.session.query(Person.username).filter_by(username=username).scalar()
    return valid


# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.args.get("username"):
        username = request.args.get("username")
        if validateUser(username):
            user = Person.query.filter_by(username=username).first()
            login_user(user) 
            return redirect(url_for('index'))
        else:
            flash(f"User with username: {username} not found")
    return render_template('login.html')


# SIGNUP PAGE
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if not request.form['username']:
            flash("Please enter a unique username")
        else:
            username = request.form['username']
            if not validateUser(username):
                user = Person(username)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash("That username is already in use. Please enter a new one.")
    return render_template("signup.html")


# LOGOUT FUNCTION
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

app.run()