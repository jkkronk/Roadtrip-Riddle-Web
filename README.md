# quiz-game

This is a flask / python app for a riddle game. The app is refreshing the riddles once 24h. 

Have fun!

## Installation

## Usage
```bash
export RR_DATA_PATH=/path/to/quiz-game/data
export FLASK_USER=admin_user
export FLASK_PASSWORD=your_password
export GOOGLE_OAUTH_KEY=your_key
export GOOGLE_OAUTH_SECRET=your_secret
export FLASK_APP=server.py
flash run
```

The riddles can be updated by calling the following url:
```bash
curl admin::password http://localhost:5000/clear_quiz
curl admin::password http://localhost:5000/new_quiz
curl admin::password http://localhost:5000/new_frames
curl admin::password http://localhost:5000/new_video
curl admin::password http://localhost:5000/clear_highscore 
```

