import os
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip, AudioClip, concatenate_audioclips, clips_array, CompositeAudioClip


def images_to_video(folder, image_duration=0.3, frame_rate=24, video_codec=cv2.VideoWriter_fourcc(*'MP4V')):
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


def create_new_video(data_dir="/var/data/", out_dir="", add_music=True):
    """
    Creates a new video from the images in the data_dir
    :param data_dir: path to the data directory
    :param out_dir: path to the output directory
    :param add_silent_audio: whether to add silent audio to the video
    :return:
    """
    # Load all images from data_dir
    images_to_video(data_dir)
    # Load the video file
    video_clip = VideoFileClip(os.path.join(data_dir, "quiz_no_audio.mp4"))
    # Load the audio file
    audio_clip = AudioFileClip(os.path.join(data_dir, "quiz.mp3"))
    audio_duration = audio_clip.duration  # Get the final audio duration
    video_duration = video_clip.duration  # Get the original video duration

    if add_music:
        # Load the music file and adjust its duration to match the video clip
        music_clip = AudioFileClip("./static/music.mp3").set_duration(audio_duration)
        # Mix the original audio with the music
        audio_clip = CompositeAudioClip([audio_clip, music_clip.volumex(0.3)])  # Adjust volume of music as needed

    # Calculate the start time for the new subclip to match the audio duration
    start_time = max(0, video_duration - audio_duration)  # Ensure start_time is not negative
    # Create a new subclip from the video_clip starting from start_time to the end
    new_video_clip = video_clip.subclip(start_time, video_duration)
    # Now, you can set the audio of the new_video_clip to final_audio
    final_clip = new_video_clip.set_audio(audio_clip)

    # Write the result to a file
    if out_dir == "":
        out_dir = data_dir
    final_clip.write_videofile(os.path.join(out_dir, "quiz.mp4"), codec='libx264', audio_codec='aac')
