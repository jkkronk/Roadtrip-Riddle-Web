import os
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip, AudioClip, concatenate_audioclips, CompositeVideoClip, \
    ImageClip, concatenate_videoclips
import instructor
import requests
from PIL import Image as PILImage
from openai import OpenAI
from io import BytesIO
import numpy as np


def images_to_video(folder, image_duration=0.4, frame_rate=24, video_codec=cv2.VideoWriter_fourcc(*'MP4V')):
    """
    Creates a video from a folder of images
    :param folder: path to the folder containing the images
    :param image_duration: in seconds
    :param frame_rate: frames per second
    :param video_codec: what codec to use for the video
    :return:
    """
    frame_folder = os.path.join(folder, "frames")
    # Get sorted list of image filenames
    filenames = [f for f in os.listdir(frame_folder) if f.endswith((".jpg", ".jpeg"))]
    sorted_filenames = sorted(filenames, key=lambda x: int(x.split('.')[0]))

    if not sorted_filenames:
        raise ValueError("No images found in the folder")

    # Read the first image to get the size
    first_image = cv2.imread(os.path.join(frame_folder, sorted_filenames[0]))
    height, width, layers = first_image.shape

    # Define the codec and create VideoWriter object
    out = cv2.VideoWriter(os.path.join(folder, "quiz_no_audio.mp4"), video_codec, frame_rate, (width, height))

    frame_count = int(frame_rate * image_duration)

    for filename in sorted_filenames:
        frame = cv2.imread(os.path.join(frame_folder, filename))

        # Check if image sizes are consistent
        if frame.shape[0] != height or frame.shape[1] != width:
            raise ValueError(f"Image size for {filename} does not match the first image size")

        # Write the frame multiple times to meet the desired duration per image
        for _ in range(frame_count):
            out.write(frame)

    out.release()


def create_new_video(data_dir="/var/data/", out_dir=""):
    """
    Creates a new video from the images in the data_dir
    :param data_dir: path to the data directory
    :return:
    """
    # Load all images from data_dir
    images_to_video(data_dir)
    # Load the video file
    video_clip = VideoFileClip(os.path.join(data_dir, "quiz_no_audio.mp4"))
    # Load the audio file
    audio_clip = AudioFileClip(os.path.join(data_dir, "quiz.mp3"))
    # Create a silent audio clip with a duration of 5 seconds
    silent_clip = AudioClip(lambda t: [0] * 2, duration=5, fps=44100)
    final_audio = concatenate_audioclips([audio_clip, silent_clip])
    final_clip = video_clip.set_audio(final_audio)

    # Write the result to a file
    if out_dir == "":
        out_dir = data_dir
    final_clip.write_videofile(os.path.join(out_dir, "quiz.mp4"), codec='libx264', audio_codec='aac')


def add_destination_to_video(path="/var/data/quiz.mp4", destination="", mobile=False):
    """
    Add two seconds in the end of the clip with a Dalle generated still image of the destination.
    :param path: path to the video file
    :param destination: The true destination of the quiz
    :return:
    """
    if mobile:
        size = "1024x1792"
    else:
        size = "1792x1024"

    image_prompt = f"An image of {destination}"
    client = instructor.patch(OpenAI())
    response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size=size,
        quality="hd",
        n=1,
    )

    response = requests.get(response.data[0].url)
    image = PILImage.open(BytesIO(response.content))

    original_clip = VideoFileClip(path)
    image = image.resize(original_clip.size)

    image_clip = ImageClip(np.array(image)).set_duration(2)  # 2 seconds long

    final_clip = concatenate_videoclips([original_clip, image_clip])

    output_path = path.replace(".mp4", "_with_destination.mp4")  # Creating a new output path
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")


def add_background_to_video(path="/var/data/quiz.mp4", destination=""):
    """
    Add background to image so it's 720x1280
    :param path: path to the video file
    :return:
    """

    image_prompt = f"A background for a video that goes to {destination}"
    client = instructor.patch(OpenAI())
    response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1792",
        quality="hd",
        n=1,
    )

    response = requests.get(response.data[0].url)
    image = PILImage.open(BytesIO(response.content))
    image = image.resize((720, 1280))

    background_clip = ImageClip(np.array(image)).set_duration(VideoFileClip(path).duration)

    # Load the original video clip
    original_clip = VideoFileClip(path)

    # Calculate position to center the video on the background
    video_position = ((720 - original_clip.size[0]) / 2, (1280 - original_clip.size[1]) / 2)

    # Overlay the original video on the background
    final_clip = CompositeVideoClip([background_clip, original_clip.set_position(video_position)], size=(720, 1280))

    # Export the final video
    output_path = path.replace(".mp4", ".mp4")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
