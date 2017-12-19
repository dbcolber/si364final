__author__ = "Danielle Colbert"

import requests
import json

import unittest
# from app import create_app, db
# from app.models import User, Role

import os
from flask import Flask, render_template, session, redirect, request, url_for, flash

from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from sqlalchemy.ext.declarative import declarative_base

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand

from flask_mail import Mail, Message
from threading import Thread
from werkzeug import secure_filename

from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

# Configuring basedir of app
basedir = os.path.abspath(os.path.dirname(__file__))

# Configuring app
app = Flask(__name__)
app.static_folder = 'static'
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/new_data_flask"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587 #default
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_SUBJECT_PREFIX'] = '[My Virtual Cookbook]'
app.config['MAIL_SENDER'] = 'Admin <danielle.colbert.4@gmail.com>' # TODO fill in 
app.config['ADMIN'] = 'Admin <danielle.colbert.4@gmail.com>'

mail = Mail(app)

manager = Manager(app)
db = SQLAlchemy(app) # For database use
migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand)

# Creating a log manager // configuring login setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)

def send_asyncronous_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject, sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_asyncronous_email, args=[app, msg])
    thr.start()

# SETTING UP MODELS ----------------------------------------------------------

# Setting up association tables

# user_recipes = db.Table('user_recipes',db.Column('user_id', db.Integer, db.ForeignKey('users.id')), db.Column('recipes_id', db.Integer, db.ForeignKey('recipes.id')))

search_recipes = db.Table('search_recipes', db.Column('recipes_id', db.Integer, db.ForeignKey('recipes.id')), db.Column('searchword_id',db.Integer, db.ForeignKey('searchwords.id'), primary_key=True))


# User Model -----------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Other models -----------------------------------------------------------------

class Searchword(db.Model):
    __tablename__ = "searchwords"
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(300))
#    recipes = db.Column(db.Integer, db.ForeignKey("recipes.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    recipes = db.relationship("Recipes", secondary = search_recipes, backref=db.backref('searchwords', lazy='dynamic'), lazy='dynamic')
    # print('from Searchword class: ', recipes)

class Recipes(db.Model):
    __tablename__ = "recipes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))
    searchword_id = db.Column(db.Integer, db.ForeignKey("searchwords.id"))
    publisher = db.Column(db.String(300))
    url = db.Column(db.String(600))
    image_url = db.Column(db.String(600))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))


# Setting up Forms -------------------------------------------------------------

class UserForm(FlaskForm):
    email=StringField('Enter Email: ', validators=[Required(), Email(), Length(1,64)])
    username=StringField('Enter Username: ', validators=[Required(), Length(1,64), Regexp('^[A-Za-z][A-Za-z0-9]*$', 0, 'Usernames can only have numbers and letters!')])
    password=PasswordField('Enter Password: ', validators=[Required(), EqualTo('password2', message="These passwords must match!")])
    password2=PasswordField('Confirm Password: ', validators=[Required()])
    submit=SubmitField('Register')


    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Sorry! This email is already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class RecipeForm(FlaskForm):
    searchword = StringField("Search for a Recipe: ", validators=[Required()])
    submit = SubmitField('Search')

# Helper functions -----------------------------------------------------------------


def get_or_create_searchword(db_session, searchword, user_id):
    print(searchword)
    searchword1 = db_session.query(Searchword).filter_by(word=searchword).first()
    if searchword1:
        print("Found recipe...")
        return searchword1
    else:
        print("Finding recipe for: ", searchword)
        searchword = Searchword(word=searchword, user_id=user_id)
        db_session.add(searchword)
        db_session.commit()
        return searchword


def get_or_create_recipes(db_session, title, publisher, url, image_url, user_id, searchword):
    recipe = db_session.query(Recipes).filter_by(name="title").first()
    if recipe:
        return recipe
    else:
        recipe_searchword = get_or_create_searchword(db_session, searchword, user_id)
        # search = recipe_searchword.id
        # recipe.searchword_id = search
        print('recipe searchword: ', recipe_searchword)

        recipe = Recipes(name=title, publisher=publisher, url=url, image_url=image_url, user_id=user_id)
        print("Recipe: ", recipe)
        db_session.add(recipe)
        db_session.commit()
        return recipe


## ROUTES -------------------------------------------------------------------

@app.errorhandler(404)
def pagenotfound(e):
	return render_template('404.html'), 404

@app.errorhandler(404)
def pagenotfound(e):
    return render_template('500.html'), 500

#VIEW FUNCTION 1
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Uh-oh! That username and/or password is invalid. Please try again!')
    return render_template('login.html',form=form)

#VIEW FUNCTION 2
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

#VIEW FUNCTION 3
@app.route('/register',methods=["GET","POST"])
def register():
    form = UserForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        mess = "Thank you for joining Virtual Cookbook!"
        send_email(form.email.data, "New Virtual Cookbook Account", "mail/register")
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

#VIEW FUNCTION 4
@app.route('/', methods=['GET', 'POST'])
def index():
    recipes = Recipes.query.all()
    form = RecipeForm()
    if form.validate_on_submit():
        base = 'http://food2fork.com/api/search'
        r = requests.get(base, params={'key':'ea94673565a10487854263cbdb7fc32c', 'q':form.searchword.data})
        r_dic = r.json()
        recipe1 = r_dic['recipes'][0]
        print(recipe1)
        print(r_dic)
        #user = User.query.filter_by(user_id=current_user.id).all()
        get_or_create_recipes(db.session, recipe1["title"], recipe1["publisher"], recipe1["source_url"], recipe1["image_url"], current_user.id, form.searchword.data)
        return redirect(url_for('see_all'))
    return render_template('index.html', form=form)

#VIEW FUNCTION 5
@app.route('/cookbook')
def see_all(methods=["GET","POST"]):
    rec = Recipes.query.all()
    all_recipes = []
    for r in rec:
        if r.user_id == current_user.id:
            all_recipes.append((r.name, r.url, r.image_url))
    return render_template('all_recipes.html', all_recipes=all_recipes)


if __name__ == '__main__':
    db.create_all()
    manager.run()


# class FlaskClientTestCase(unittest.TestCase):
#     # testing the addition of a new recipe to the database
#     def test_recipes(self):
#         # adding a new recipe
#         new_recipe = get_or_create_recipes(db.session, 'Paleo Pancakes', 'Cooking by Danielle', 'www.test123.com', 'www.test123.com/images', 4)
#         db.session.add(new_recipe)
#         db.session.commit()

#         # testing to see if user is in db
#         rec = Recipes.query.filter_by(name='Paleo Pancakes').first()
#         self.assertEqual(rec.name, 'Paleo Pancakes')

# if __name__ == '__main__':
#     unittest.main()





