import os
import json
from moviepy.editor import VideoFileClip, AudioFileClip

from quiz.audio_creator import create_audio
from quiz.image_collector import ImageCollector
from quiz.video_creator import images_to_video, create_new_video
from quiz.utils import random_destination
from quiz.quiz_clues import QuizClues, QuizCluesWithAudio
from quiz.quiz_creator import create_quiz
from quiz.map_creator import save_maps_for_coordinates

def main(data_dir='/Users/JonatanMBA/Documents/code/Roadtrip-Riddle-Web/data/', fps=12, cache=True):
    """
    Main function to create a quiz, generate audio clues, collect images, create a video, and combine them.
    """

    city = "zurich"  
    if city == "":
        city = random_destination("./static/cities.txt")
    data_dir = os.path.join(data_dir, city.lower())
    os.makedirs(data_dir, exist_ok=True)
    quiz_file = os.path.join(data_dir, "manuscript.json")

    if not os.path.exists(quiz_file) or not cache:
        print(f"No quiz file found. Creating new quiz.")
        quiz = create_quiz(city)
        quiz.save(city, quiz_file)
    else:
        print(f"Quiz file already exists. Loading existing quiz.")
        quiz = QuizClues.open(quiz_file)

    audio_file = os.path.join(data_dir, "audio_manuscript.json")
    if not os.path.exists(audio_file) or not cache:
        quiz = create_audio(quiz, use_elevenlabs=True, elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"))        
        quiz.save(city, audio_file)
    else:
        quiz = QuizCluesWithAudio.open(audio_file)
        print(f"Audio file already exists in {data_dir}")
    
    images_folder = os.path.join(data_dir, 'images')
    if not os.path.exists(os.path.join(data_dir, 'images')) or not cache:
        os.makedirs(images_folder, exist_ok=True)
        collector = ImageCollector(city, images_folder)
        route, bearings = collector.collect_images()
        with open(os.path.join(data_dir, 'collected_image_coords.json'), 'w') as f:
            json.dump(route, f)
    else:
        print(f"Images already exist in {data_dir}")
        with open(os.path.join(data_dir, 'collected_image_coords.json'), 'r') as f:
            collected_image_coords = json.load(f)
    
    # map_path = os.path.join(data_dir, 'images', 'map_frames')
    # if not os.path.exists(map_path) or not cache:
    #     os.makedirs(map_path, exist_ok=True)
    #     save_maps_for_coordinates(collected_image_coords, output_prefix=map_path + "/map_", width=1080, height=960)
    map_path = None
    frame_folder = images_folder
    out_folder = os.path.join(data_dir, 'videos')
    if not os.path.exists(os.path.join(data_dir, 'videos')) or not cache:
        os.makedirs(out_folder, exist_ok=True)
        images_to_video(frame_folder=os.path.join(frame_folder, "street_view_frames"), frame_folder_second=map_path, out_folder=out_folder, frame_rate=fps, size=(1080, 960))
    else:
        print(f"Video already exists in {data_dir}")

    if os.path.exists(os.path.join(data_dir, 'videos', 'quiz_no_audio.mp4')) or not cache:   
        video_path = os.path.join(out_folder, "quiz_no_audio.mp4")
        video_clip = VideoFileClip(video_path)
        audio = quiz.get_complete_audio()
        temp_audio_path = os.path.join(out_folder, "temp_audio.mp3")
        audio.export(temp_audio_path, format="mp3")
        audio_clip = AudioFileClip(temp_audio_path)
        create_new_video(video_clip, audio_clip, out_folder)
        os.remove(temp_audio_path)

if __name__ == "__main__":
    main()