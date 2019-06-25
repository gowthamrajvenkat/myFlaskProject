from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from data import Articles
from datetime import datetime
import sys
from functools import wraps

app = Flask(__name__)
db = SQLAlchemy(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.jinja_env.globals.update(zip=zip)
app.secret_key = 'secret123'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(25), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    register_date = db.Column(db.DateTime, default = datetime.utcnow)
    
    def __repr__(self):
        return '<User %r>' % self.id

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    create_date = db.Column(db.DateTime, default = datetime.utcnow)
    
    def __repr__(self):
        return '<Article %r>' % self.id

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password',[
                validators.DataRequired(),
                validators.EqualTo('confirm', message='Passwords do not match')
                ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        
        new_user = User(name = name, email = email, username = username, password = password)

        try:
            db.session.add(new_user)
            db.session.commit()

            flash('You are now registered and can log in', 'success')

            return redirect(url_for('login'))
        except:
            flash(sys.exc_info()[0], 'failure')

        return render_template('register.html', form=form)
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        #DB code
        data = User.query.filter_by(username=username).first()
        if data is not None:
            # Get stored hash
             #get the first one from query
            app.logger.info(data)
            password = data.password

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                #Passed  app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login','danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    articles = Article.query.filter_by(author=session['username']).order_by(Article.id).all()
    if len(articles) > 0:
        app.logger.info(articles)
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])
    
@app.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        new_article = Article(title = title, body = body, author = session['username'])
        try:
            db.session.add(new_article)
            db.session.commit()

            flash('Article Created', 'success')

            return redirect(url_for('dashboard'))
        except:
            flash(sys.exc_info()[0], 'danger')

    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    article = Article.query.filter_by(id=id).first()

    form = ArticleForm(request.form)

    form.title.data = article.title
    form.body.data = article.body
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        #article_to_edit = Article(title = title, body = body, author = session['username'])
        article.title = title
        article.body = body
        try:
            #db.session.add(new_article)
            db.session.commit()

            flash('Article Updated', 'success')

            return redirect(url_for('dashboard'))
        except:
            flash(sys.exc_info()[0], 'danger')

    return render_template('edit_article.html', form=form)

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    article = Article.query.filter_by(id=id).first()
    try:
        db.session.delete(article)
        db.session.commit()
        flash('Article Deleted', 'success')

        return redirect(url_for('dashboard'))
    except:
        flash(sys.exc_info()[0], 'danger')


Articles = Articles()

@app.route('/')
def hello(name = None):
    return render_template('index.html',name=name)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    articles = Article.query.order_by(Article.id).all()
    if articles is not None:
        app.logger.info(articles)
        createdates = [-1*(article.create_date - datetime.utcnow()) for article in articles]
        return render_template('articles.html', articles=articles, datediff=createdates)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)

@app.route('/article/<string:id>')
def article(id):
    article = Article.query.filter_by(id =id).first()
    if article is not None:
        app.logger.info(articles)
        return render_template('article.html', article=article)
    else:
        msg = 'No Article Found'
        return render_template('article.html', msg=msg)


