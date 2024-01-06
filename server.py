import random
import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_oauthlib.client import OAuth

import utils

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.secret_key = os.urandom(24)  # Generate a random key

db = SQLAlchemy(app)

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key='933964174540-8ij15f7ne7s88m7s748jvr19u9vsmdug.apps.googleusercontent.com',
    consumer_secret=os.environ.get('GOOGLE_OAUTH_SECRET'),
    request_token_params={
        'scope': ['email', 'https://www.googleapis.com/auth/userinfo.profile']
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

# Route for the home page
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')


# Route for the video page
@app.route('/video')
def video():
    # Path to the text file with the answer
    correct_answer = utils.get_answer(os.path.join(app.static_folder, 'quiz.json'))
    start_time = time.time()
    return render_template('video.html', start_time=start_time, correct_answer=correct_answer)


@app.route('/high_scores')
def high_scores():
    daily_scores = HighScore.query.order_by(HighScore.daily_score.desc()).all()
    all_time_high_scores = HighScore.query.order_by(HighScore.total_score.desc()).all()
    return render_template('high_scores.html', all_time_high_scores=all_time_high_scores, daily_high_scores=daily_scores)


@app.route('/info')
def info():
    return render_template('info.html')


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    video_file_path = os.path.join(app.static_folder, 'quiz.mp4')
    start_time = float(request.form['start_time'])
    end_time = time.time()
    time_taken = end_time - start_time
    score = utils.calculate_score(time_taken, video_file_path)
    session['latest_score'] = score  # Storing the latest score in session
    return redirect(url_for('score', score=score))

# Route for the score page
@app.route('/score/<score>')
def score(score):
    daily_scores = HighScore.query.order_by(HighScore.daily_score.desc()).all()
    return render_template('score.html', score=score, daily_high_scores=daily_scores)


@app.route('/login')
def login():
    session['score_to_submit'] = request.args.get('score')
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None or resp.get('access_token') is None:
        # Handle the error appropriately
        return 'Access Denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    session['google_token'] = (resp['access_token'], '')
    if 'score_to_submit' in session:
        score = session.pop('score_to_submit')
        return redirect(url_for('submit_score', score=score))
    else:
        return redirect(url_for('home'))


@app.route('/submit_score')
def submit_score():
    if 'google_token' not in session:
        return redirect(url_for('login'))

    score = request.args.get('score')
    user_info = google.get('userinfo').data
    google_user_id = user_info.get('id')
    user_name = user_info.get('name', 'Unknown User')

    existing_score = HighScore.query.filter_by(google_user_id=google_user_id).first()

    if existing_score and existing_score.daily_score != -1:
        # User already submitted a score today
        return redirect(url_for('already_submitted'))  # Redirect or handle as needed
    else:
        # Either no score submitted today or score is -1
        if existing_score:
            # Update existing score
            existing_score.daily_score = score
        else:
            # Create new score entry
            new_score = HighScore(google_user_id=google_user_id, daily_score=score, total_score=score)
            db.session.add(new_score)

        db.session.commit()
        return redirect(url_for('high_scores'))


@app.route('/already_submitted')
def already_submitted():
    return render_template('already_submitted.html')


class HighScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_user_id = db.Column(db.String(100))
    user_name = db.Column(db.String(50))
    daily_score = db.Column(db.Integer)
    total_score = db.Column(db.Integer)

    def __repr__(self):
        return '<HighScore %r>' % self.user_name


with app.app_context():
    db.create_all()


@app.route('/explanations')
def explanations():
    clues_and_explanations = utils.get_explanations(os.path.join(app.static_folder, 'quiz.json'))
    return render_template('explanations.html', explanations=clues_and_explanations)


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


# Initialize Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=utils.create_new_video, trigger="cron", hour=0)
scheduler.add_job(func=utils.clear_daily_high_scores, trigger="cron", hour=0)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True)
