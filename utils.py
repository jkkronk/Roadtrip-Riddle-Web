from moviepy.editor import VideoFileClip
import json
import os
import shutil
from datetime import datetime, timedelta, time
import pytz

def get_expiration_time():
    # Define the timezone
    timezone = pytz.timezone('Europe/Brussels')  # Use the appropriate European timezone

    # Get the current time in the specified timezone
    now = datetime.now(timezone)

    # Define the expiration time as 05:00
    expiration_time = time(5, 0, 0)

    # Combine the current date and the expiration time
    expiration_datetime = datetime.combine(now.date(), expiration_time, tzinfo=timezone)

    # If it's already past 05:00, set the expiration for the next day
    if now.time() > expiration_time:
        expiration_datetime += timedelta(days=1)

    return expiration_datetime

# Function to calculate the score
def calculate_score(time_taken, video_file_path):
    if time_taken <= 0:
        raise ValueError("time_taken must be a positive number")
    if not os.path.isfile(video_file_path):
        raise ValueError("video_file_path is not a valid file path")

    with VideoFileClip(video_file_path) as video:
        video_duration = video.duration

    # Calculate the score as a percentage
    if time_taken > video_duration:
        return 0  # If the time taken is more than the video duration, return 0%
    else:
        return int(((video_duration - time_taken) / video_duration) * 100)
def get_answer(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data["city"]

def get_explanations(file_path):
    # Load the JSON data
    with open(file_path) as f:
        quiz_data = json.load(f)
    explanations = quiz_data.get('explanations', [])
    clues = quiz_data.get('clues', [])
    clues_and_explanations = []
    for idx, clue in enumerate(clues):
        clues_and_explanations.append("<b>🚗 " + clue + "</b>")
        clues_and_explanations.append("💡 " + explanations[idx] + "<br><br>")

    return clues_and_explanations

def remove_files_and_folders(folder_path):
    # Check each item in the folder
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        # If the item is a file, remove it
        if os.path.isfile(item_path) and not item_path.endswith('.db'):
            os.remove(item_path)
        # If the item is a directory, remove the directory and its contents
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

