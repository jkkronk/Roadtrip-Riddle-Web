import time
import os
from flask import Flask, request, render_template, redirect, url_for, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_oauthlib.client import OAuth
from flask_httpauth import HTTPBasicAuth

import utils
from quiz import quiz_creator, street_view_collector, video_creator

app = Flask(__name__)
#app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:////var/data/users.db"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.secret_key = os.urandom(24)  # Generate a random key
auth = HTTPBasicAuth()

users = {
    os.environ.get('FLASK_USER'): os.environ.get('FLASK_PASSWORD')
}

db = SQLAlchemy(app)

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=os.environ.get('GOOGLE_OAUTH_KEY'),
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


@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Home page
    """
    return render_template('home.html')


@app.route('/get_video')
def get_video():
    """
    Get the video file
    """
    video_path = f"{os.environ.get('RR_DATA_PATH')}quiz.mp4"
    return send_file(video_path, as_attachment=True)


# Route for the video page
@app.route('/video')
def video():
    """
    Video page
    """
    # Check if the user has a valid cookie
    if request.cookies.get('played_today'):
        # Redirect to score if they've already played today
        return redirect(url_for('score'))

    # Rest of your existing code
    quiz_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.json")
    correct_answer = utils.get_answer(quiz_path)
    return render_template('video.html', correct_answer=correct_answer)


@app.route('/high_scores')
def high_scores():
    """
    High scores page
    """
    daily_scores = HighScore.query.order_by(HighScore.daily_score.desc()).all()
    all_time_high_scores = HighScore.query.order_by(HighScore.total_score.desc()).all()
    return render_template('high_scores.html', all_time_high_scores=all_time_high_scores,
                           daily_high_scores=daily_scores)


@app.route('/info')
def info():
    """
    Info page
    """
    return render_template('info.html')


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """
    Handle the answer submission
    """
    video_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.mp4")
    start_time = float(request.form['start_time'])
    end_time = time.time()
    time_taken = end_time - start_time
    score = utils.calculate_score(time_taken, video_path)
    session['latest_score'] = score

    # Set a cookie that expires in 24 hours
    resp = make_response(redirect(url_for('score')))
    expiration_datetime = utils.get_expiration_time()
    resp.set_cookie('played_today', 'true', expires=expiration_datetime)
    return resp


# Route for the score page
@app.route('/score')
def score():
    """
    Score page
    """
    score = session.get('latest_score', 0)  # Default to 0 if not found in session
    daily_scores = HighScore.query.order_by(HighScore.daily_score.desc()).all()
    quiz_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.json")
    correct_answer = utils.get_answer(quiz_path)
    return render_template('score.html', score=score, daily_high_scores=daily_scores, correct_answer=correct_answer)


@app.route('/login')
def login():
    """
    Sends the user to the google login page
    """
    session['score_to_submit'] = request.args.get('score')
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
def authorized():
    """
    Handles the google login callback
    """
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
    """
    Submit the score to the database
    """
    if 'google_token' not in session:
        return redirect(url_for('login'))

    score = request.args.get('score')
    user_info = google.get('userinfo').data
    google_user_id = user_info.get('id')

    existing = HighScore.query.filter_by(google_user_id=google_user_id).first()

    if existing and existing.daily_score != -1:
        # User already submitted a score today
        return redirect(url_for('already_submitted'))  # Redirect or handle as needed
    else:
        # Either no score submitted today or score is -1
        if existing:
            # Update existing score
            existing.daily_score = score
            existing.total_score += int(score)
        else:
            session['temp_score'] = request.args.get('score')
            return render_template('enter_username.html', google_user_id=google_user_id)

        db.session.commit()
        return redirect(url_for('high_scores'))


@app.route('/submit_username', methods=['POST'])
def submit_username():
    """
    Submit the username to the database
    """
    google_user_id = request.form['google_user_id']
    username = request.form['username']

    # Check if username is good. Ie. not existing in database and not empty
    existing = HighScore.query.filter_by(user_name=username).first()
    if existing:
        return render_template('enter_username.html', google_user_id=google_user_id, error="Please enter a username")
    elif username == "":
        return render_template('enter_username.html', google_user_id=google_user_id, error=f"You can't be named: {username}")

    score = session.pop('temp_score', 0)  # Default to 0 if not found

    # Create new score entry with the username
    new_score = HighScore(google_user_id=google_user_id, user_name=username, daily_score=score, total_score=score)
    db.session.add(new_score)
    db.session.commit()

    # Redirect to the appropriate page after username submission
    return redirect(url_for('high_scores'))


@app.route('/already_submitted')
def already_submitted():
    """
    Page for when the user has already submitted a score today
    """
    return render_template('already_submitted.html')


class HighScore(db.Model):
    """
    High score model
    """
    id = db.Column(db.Integer, primary_key=True)  # User ID
    google_user_id = db.Column(db.String(100))  # Google User ID
    user_name = db.Column(db.String(50))  # User name
    daily_score = db.Column(db.Integer)  # Daily score
    total_score = db.Column(db.Integer)  # Total score

    def __repr__(self):
        return '<HighScore %r>' % self.user_name


# Create the database tables
with app.app_context():
    db.create_all()


@app.route('/explanations')
def explanations():
    """
    Explanations page
    """
    quiz_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.json")
    return render_template('explanations.html', explanations=utils.get_explanations(quiz_path))


@google.tokengetter
def get_google_oauth_token():
    """
    Get the google oauth token
    """
    return session.get('google_token')


@auth.verify_password
def verify_password(username, password):
    """
    Verify the username and password
    :param username:
    :param password:
    :return:
    """
    if username in users and users[username] == password:
        return username


@app.route('/clear_highscore')
@auth.login_required
def clear_highscore():
    """
    Clear the high scores
    """
    with app.app_context():  # This line creates the application context
        try:
            # Reset daily scores for all users
            HighScore.query.update({HighScore.daily_score: -1})
            db.session.commit()
        except Exception as e:
            print("Error resetting daily high scores:", e)
            db.session.rollback()
    return "Highscores cleared!"


@app.route('/clear_quiz')
@auth.login_required
def clear_quiz():
    """
    Clear the quiz
    """
    utils.remove_files_and_folders(os.environ.get('RR_DATA_PATH'))
    return "Quiz cleared!"


@app.route('/new_quiz')
@auth.login_required
def new_quiz():
    """
    Create a new quiz
    """
    quiz_creator.create_new_quiz(os.environ.get('RR_DATA_PATH'))
    return "Quiz created!"


@app.route('/new_frames')
@auth.login_required
def new_frames():
    """
    Create new frames
    """
    street_view_collector.create_new_frames(os.environ.get('RR_DATA_PATH'))
    return "Frames created!"


@app.route('/new_video')
@auth.login_required
def new_video():
    """
    Create a new video
    """
    video_creator.create_new_video(os.environ.get('RR_DATA_PATH'))
    return "Video created!"


if __name__ == '__main__':
    app.run(debug=False)
