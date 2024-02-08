# quiz-game

This is a flask / python app for a riddle game. It uses gpt-4 to create a quiz and clues + explanations. Additionally, 
a stop-motion video is created using google map api. 

Here is the app deployed on render: https://roadtrip-riddle.onrender.com

<img src="misc/home_page.png">
<img src="misc/quiz_page.png">
<img src="misc/score_page.png">

## Installation
```bash
git clone
cd quiz-game
pip3 install -r requirements.txt
```

## Usage
```bash
export RR_DATA_PATH=/path/to/quiz-game/data
export FLASK_USER=admin_user
export FLASK_PASSWORD=your_password
export GOOGLE_OAUTH_KEY=your_key
export GOOGLE_OAUTH_SECRET=your_secret
export FLASK_APP=server.py
export GOOGLE_API_KEY=your_key
export OPENAI_API_KEY=your_key
gunicorn --timeout 600 server:app
```

The riddles can be updated by calling the following url:
```bash
curl admin::password http://localhost:5000/clear_quiz
curl admin::password http://localhost:5000/new_quiz
curl admin::password http://localhost:5000/new_frames
curl admin::password http://localhost:5000/new_video
curl admin::password http://localhost:5000/clear_highscore 
```

If you want to just get a mobile friendly video you can call create_sample.py as follows:
```bash
python create_sample.py ./data ./static/intro_mobile_example.txt
```

## Testing
At the moment there is only some tests implemented. The test only test util functions. No tests are done functions or 
classes with api calls. 

```bash
python3 -m unittest discover -s tests
```

