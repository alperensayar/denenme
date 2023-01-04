from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
import re

from flask_cors import CORS
import psycopg2


conn = psycopg2.connect(
    host="8.tcp.ngrok.io",
    database="user_path",
    user="postgres",
    password="postgres",
    port="15188"
)

# Open a cursor to perform database operations
cur = conn.cursor()
app = Flask(__name__)
cors = CORS(app)

app.config.from_pyfile('config.cfg')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'kerem-ahmet'

mail = Mail(app)
s = URLSafeTimedSerializer('Thisisasecret!')

db = SQLAlchemy(app)
db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'signin'
login_manager.init_app(app)

class Survey(db.Model):
    __tablename__ = 'surveys'
    token_id = db.Column(db.String(), unique=True, primary_key=True)
    sender = db.Column(db.String(100))
    reporting_mail = db.Column(db.String(100))
    recepient = db.Column(db.String(100))
    survey_type = db.Column(db.String(100))
    language = db.Column(ARRAY(db.String(20)))
    send_time = db.Column(db.DateTime(datetime.now()))
    is_done = db.Column(db.Boolean, default=False)

    def __init__(self, token_id, sender, reporting_mail, recepient, survey_type, language, send_time):
        self.token_id = token_id
        self.sender = sender
        self.reporting_mail = reporting_mail
        self.recepient = recepient
        self.survey_type = survey_type
        self.language = language
        self.send_time = send_time

class User(UserMixin, db.Model):
  __tablename__='users'
  id=db.Column(db.Integer,primary_key=True)
  email = db.Column(db.String(100), unique=True)
  username=db.Column(db.String(100))
  password=db.Column(db.String(100))
  company=db.Column(db.Integer, db.ForeignKey('company.company_id'))

  def __init__(self,email,username,password,company):
    self.email = email
    self.username=username
    self.password=password
    self.company=company

class Company(db.Model):
    __tablename__ = 'company'
    company_id = db.Column(db.Integer, unique=True, primary_key=True)
    company_name = db.Column(db.String(100))
    company_mail = db.Column(db.String(100))
    users = db.relationship('User', backref='company_ref', lazy=True)

    def __init__(self, company_id, company_name, company_mail):
        self.company_id = company_id
        self.company_name = company_name
        self.company_mail = company_mail
db.create_all()
@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))

# Home page, nothing here
@app.route('/')
def index():
    return render_template('index.html')

# Page where user signs up
@app.route('/signup')
def signup():
    return render_template('register.html')

# Page where user signs in
@app.route('/signin')
def signin():
    return render_template('login.html')

# Page where user enters after successful login and user can log out
@app.route('/home')
@login_required
def home():
    return render_template('send_survey.html', data=current_user.username)

@app.route('/survey1')
@login_required
def survey1():
    return render_template('survey1.html')

# When user clicks sign up button to sign up
@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    special_id = request.form.get('special_id')

    company = Company.query.filter_by(company_id=special_id).first()

    if not company:
        flash('Lütfen geçerli ID giriniz.')
        return redirect(url_for('signup'))

    if not password == confirm_password: # if passwords don't match, remind user
        flash('Lütfen şifreleri aynı giriniz.')
        return redirect(url_for('signup'))

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Bu e-posta kullanımda bulunmaktadır.')
        return redirect(url_for('signup'))

    # create a new user with the form data
    new_user = User(email=email, username=username, password=password, company=company.company_id)

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('signin'))

# When user clicks sign in button to sign in
@app.route('/signin', methods=['POST'])
def signin_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    user = User.query.filter_by(email=email).first()

    # check if the user actually exists and if the password is correct
    if not user or not user.password == password:
        flash('Yanlış bilgi girdiniz.')
        return redirect(url_for('signin')) # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('home'))

# When the user clicks the logout button
@app.route('/home', methods=['POST'])
def home_post():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    logout_user()
    return redirect(url_for('signin'))

@app.route('/send-survey', methods=['GET', 'POST'])
def send_survey():
    if request.method == 'GET':
        return redirect(url_for('home'))

    recipients = request.form['email'].split(',')

    survey_type = list()
    survey_type.append('survey/') if request.form.get('survey1') == 'survey1' else None
    survey_type.append('survey_3/') if request.form.get('survey2') == 'survey2' else None
    survey_type.append('survey_2/') if request.form.get('survey3') == 'survey3' else None

    if survey_type == []:
        flash("Lütfen en az bir anket seçiniz.")
        return redirect(url_for('home'))

    languages = list()
    #languages.append('turkish') if request.form.get('languageRadios') == 'turkish' else None
    #languages.append('english') if request.form.get('languageRadios') == 'english' else None
    #languages.append('german') if request.form.get('languageRadios') == 'german' else None

    languages.append(request.form.get('languageRadios'))

    if recipients[0] == '':
        flash('Lütfen e-posta giriniz.')
        return redirect(url_for('send_survey'))

    company = Company.query.filter_by(company_id=current_user.company).first()
    reporting_mail = company.company_mail

    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+.[A-Z|a-z]{2,}\b'

    for recipient in recipients:
        if not re.fullmatch(regex, recipient):
            print('Invalid E-mail:', recipient)
            continue
        tokens = list()
        for st in survey_type:
            year, month, day, hour, minute, second, microsecond, send_time = get_datetime()
            lst = [recipient, st, year, month, day, hour, minute, second, microsecond,st]
            token = s.dumps(lst, salt='email-confirm')
            tokens.append(token)

        msg = Message('Anket',sender='ahmet.mail.ops@gmail.com', recipients=[recipient])
        body = ''
        my_url='https://surveygercektenson.herokuapp.com/'

        for i in range(len(tokens)):
            #link = url_for('confirm_email', token=tokens[i], _external=True)
            #body += 'Your link for {} is {}\n\n'.format(survey_type[i], link)
            body += 'Your link for {}{}{}\n\n'.format(my_url,survey_type[i],tokens[i])
            survey = Survey(tokens[i], current_user.email, reporting_mail, recipient, survey_type[i], languages, send_time)
            postgres_insert_query = """ INSERT INTO path_table (path_name, durum) VALUES (%s,%s)"""
            record_to_insert = (str('/'+survey_type[i]+tokens[i]),'1')
            cur.execute(postgres_insert_query, record_to_insert)

            conn.commit()
            db.session.add(survey)
            db.session.commit()
        msg.body = body
        mail.send(msg)

    output = 'Anketler gönderildi.'
    flash(output)
    return redirect(url_for('home'))

@app.route('/survey1', methods=['POST'])
def survey1_complete():
    return redirect(url_for('home'))

@app.route('/survey/<token>')
def confirm_email(token):
    # db istek at kontrol et if else ile kontrol et
    survey_result = Survey.query.filter_by(token_id=token).first()
    if survey_result is None:
        return '<h1>Bu token geçerli değil.</h1>'
    is_done = survey_result.is_done
    try:
        if not is_done:
            lst = s.loads(token, salt='email-confirm', max_age=3600)
            email = lst[0]
            survey_type = lst[1]
            send_date = datetime(lst[2], lst[3], lst[4], lst[5], lst[6], lst[7], lst[8])
            if survey_type == 'survey1':
                return redirect(url_for('survey1'))
            elif survey_type == 'survey2':
                return render_template('survey2.html')
            elif survey_type == 'survey3':
                return render_template('survey3.html')
            else:
                flash('Bir sorun çıktı.')
                return redirect(url_for('index'))
        else:
            flash('Bu token önceden kullanılmıştır.')
            return redirect(url_for('index'))

    except SignatureExpired:
        flash('Bu tokenin süresi dolmuştur.')
        return redirect(url_for('index'))


@app.route('/urlpoint', methods=['POST'])
def url_Check():
    my_url = request.get_json()
    print("my_url", my_url)
    sql = "UPDATE path_table SET durum = '3' WHERE path_name = %s"
    cur.execute(sql,(my_url["path"],))
    conn.commit()
    return my_url


@app.route('/getresult', methods=['POST'])
def url_Check12():
    my_url12 = request.get_json()
    print("my_url12", my_url12)
    return my_url12


@app.route('/apiget', methods=['POST', 'GET'])
def url_Check123():
    if request.method == 'POST':
        my_url123 = request.get_json()
        print("my_url123", my_url123)

    query = "select durum from path_table where path_name=(%s)"
    path_searcher=my_url123["path"]
    cur.execute(query,(path_searcher,))
    try:
        row=cur.fetchone()[0]
    except:
        row="0"
    #if row == None:
        #row = "0"
    print(row)

    response_body = {"durum": row}
    print(response_body)

    return response_body


def get_datetime():
    date = datetime.now()
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    second = date.second
    microsecond = date.microsecond
    return year, month, day, hour, minute, second, microsecond, date

if __name__ == '__main__':
    app.run(debug=True)
