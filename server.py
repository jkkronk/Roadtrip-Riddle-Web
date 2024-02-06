import os
from flask import Flask, request, render_template, redirect, url_for, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_oauthlib.client import OAuth
from flask_httpauth import HTTPBasicAuth
from datetime import datetime, timedelta, time
import time
import platform

from utils import get_answer, calculate_score, get_expiration_time, is_valid_username, get_explanations, \
    remove_files_and_folders
from quiz import quiz_creator, street_view_collector, video_creator

app = Flask(__name__)
if platform.system() != 'Darwin':
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:////var/data/users.db"
else:
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
    video_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.mp4")
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
    correct_answer = get_answer(quiz_path)
    return render_template('video.html', correct_answer=correct_answer)


@app.route('/high_scores')
def high_scores():
    """
    High scores page
    """
    daily_scores = User.query.order_by(User.daily_score.desc()).all()
    monthly_high_scores = get_last_month_high_scores()
    return render_template('high_scores.html', monthly_high_scores=monthly_high_scores,
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
    daily_score = calculate_score(time_taken, video_path)
    session['latest_score'] = daily_score

    # Set a cookie that expires in 24 hours
    resp = make_response(redirect(url_for('score')))
    expiration_datetime = get_expiration_time()
    resp.set_cookie('played_today', 'true', expires=expiration_datetime)
    return resp


# Route for the score page
@app.route('/score')
def score():
    """
    Score page
    """
    user_score = session.get('latest_score', 0)  # Default to 0 if not found in session
    daily_scores = User.query.order_by(User.daily_score.desc()).all()
    quiz_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.json")
    correct_answer = get_answer(quiz_path)
    return render_template('score.html', score=user_score, daily_high_scores=daily_scores,
                           correct_answer=correct_answer)


@app.route('/login')
def login():
    """
    Sends the user to the google login page
    """
    session['score_to_submit'] = request.args.get('score')
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login_for_delete')
def login_for_delete():
    next_url = request.args.get('next', url_for('high_scores'))  # Default to home if not specified
    session['next_url_after_login'] = next_url
    return google.authorize(callback=url_for('authorized_for_delete', _external=True))


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


@app.route('/login/authorized_for_delete')
def authorized_for_delete():
    resp = google.authorized_response()
    if resp is None or resp.get('access_token') is None:
        # Handle error...
        return 'Access Denied...'

    session['google_token'] = (resp['access_token'], '')
    return redirect(url_for('delete_score'))


@app.route('/submit_score')
def submit_score():
    """
    Submit the score to the database
    """
    if 'google_token' not in session:
        return redirect(url_for('login'))

    daily_score = request.args.get('score')
    try:
        daily_score = int(daily_score)  # or float(daily_score) if the score can be fractional
    except ValueError:
        # Handle the error if conversion fails
        return "Invalid score value provided", 400

    user_info = google.get('userinfo').data
    google_user_id = user_info.get('id')

    existing_user = User.query.filter_by(google_user_id=google_user_id).first()

    if existing_user and existing_user.daily_score != -1:
        # User already submitted a score today
        return redirect(url_for('already_submitted'))  # Redirect or handle as needed
    else:
        # Either no score submitted today or score is -1
        if existing_user:
            # Update existing score
            existing_user.daily_score = daily_score
            new_game_score = GameScore(score=daily_score, user_id=existing_user.id)
            db.session.add(new_game_score)
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

    # Check if username is good. Ie. not existing in database and not empty. Check if username has valid qwerty characters.
    existing = User.query.filter_by(user_name=username).first()
    if existing:
        return render_template('enter_username.html', google_user_id=google_user_id, error="Username already exists!")
    elif not is_valid_username(username):
        return render_template('enter_username.html', google_user_id=google_user_id,
                               error="Username must only contain maximum 20 letters or numbers!")

    first_score = session.pop('temp_score', 0)  # Default to 0 if not found

    # Create new score entry with the username
    new_user = User(google_user_id=google_user_id, user_name=username, daily_score=first_score)
    db.session.add(new_user)
    db.session.commit()

    # Create new score entry for the user
    new_game_score = GameScore(score=first_score, user_id=new_user.id)
    db.session.add(new_game_score)
    db.session.commit()

    # Redirect to the appropriate page after username submission
    return redirect(url_for('high_scores'))


@app.route('/already_submitted')
def already_submitted():
    """
    Page for when the user has already submitted a score today
    """
    return render_template('already_submitted.html')


@app.route('/delete_score')
def delete_score():
    if 'google_token' not in session:
        return redirect(url_for('login', next=url_for('delete_score')))

    user_info = google.get('userinfo').data
    google_user_id = user_info.get('id')

    user = User.query.filter_by(google_user_id=google_user_id).first()
    if user:
        # Delete all GameScore records associated with the user
        GameScore.query.filter_by(user_id=user.id).delete()

        # Assuming you want to set the score to -1 to indicate deletion, adjust as necessary
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('high_scores', message='Score deleted successfully.'))
    else:
        return redirect(url_for('high_scores', error='User not found.'))



class User(db.Model):
    """
    User model
    """
    id = db.Column(db.Integer, primary_key=True)  # User ID
    google_user_id = db.Column(db.String(100))  # Google User ID
    user_name = db.Column(db.String(50))  # User name
    daily_score = db.Column(db.Integer)  # Daily score
    scores = db.relationship('GameScore', backref='user', lazy=True)

    def __repr__(self):
        return '<HighScore %r>' % self.user_name


class GameScore(db.Model):
    """
    Game score model
    """
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    played_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Foreign Key to link scores to a specific user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Create the database tables
with app.app_context():
    db.create_all()


@app.route('/explanations')
def explanations():
    """
    Explanations page
    """
    quiz_path = os.path.join(os.environ.get('RR_DATA_PATH'), "quiz.json")
    return render_template('explanations.html', explanations=get_explanations(quiz_path))


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


@app.route('/clear_daily_highscore')
@auth.login_required
def clear_daily_highscore():
    """
    Clear the high scores
    """
    with app.app_context():  # This line creates the application context
        try:
            # Reset daily scores for all users
            User.query.update({User.daily_score: -1})
            db.session.commit()
        except Exception as e:
            print("Error resetting daily high scores:", e)
            db.session.rollback()
    return "Daily highscores cleared!"


@app.route('/clear_quiz')
@auth.login_required
def clear_quiz():
    """
    Clear the quiz
    """
    remove_files_and_folders(os.environ.get('RR_DATA_PATH'))
    return "Quiz cleared!"


@app.route('/new_quiz')
@auth.login_required
def new_quiz():
    """
    Create a new quiz
    """
    quiz_creator.create_new_quiz(os.environ.get('RR_DATA_PATH'))
    return "Quiz created!"


@app.route('/new_video')
@auth.login_required
def new_video():
    """
    Create new video from the quiz
    """
    street_view_collector.create_new_frames(os.environ.get('RR_DATA_PATH'))
    video_creator.create_new_video(os.environ.get('RR_DATA_PATH'))
    return "Video created!"


def get_last_month_high_scores():
    """
    Get the total scores for each user over the current month, including user names.
    """
    # Calculate the start of the current month
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)

    # Query to sum scores for each user over the current month and join with the User table to get user names
    monthly_scores = (db.session.query(
        User.user_name,  # Include user_name in the query
        func.sum(GameScore.score).label('total_score')
    ).join(User, User.id == GameScore.user_id)
                      .filter(GameScore.played_at >= start_of_month)
                      .group_by(User.id)
                      .order_by(func.sum(GameScore.score).desc())
                      .all())

    # This will return a list of tuples, each containing (user_name, total_score)
    return monthly_scores



if __name__ == '__main__':
    app.run(debug=False)
