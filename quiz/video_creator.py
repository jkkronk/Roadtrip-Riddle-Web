import os
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip, AudioClip, concatenate_audioclips, clips_array, CompositeAudioClip


def images_to_video(path, images, audio, image_duration=0.4, frame_rate=24, video_codec=cv2.VideoWriter_fourcc(*'MP4V'), zoom_variable=5):
    """
    Creates a video from a folder of images
    :param path: the folder to save the video
    :param images: the list of images
    :param audio: the audio file
    :param image_duration: the duration of each image
    :param frame_rate: the frame rate of the video
    :param video_codec: the codec to use
    :param zoom_variable:
    :return:

    """
    # Read the first image to get the size
    height, width, _ = images[0].shape

    # Define the codec and create VideoWriter object
    out = cv2.VideoWriter(path, video_codec, frame_rate, (width, height))

    frame_count = int(frame_rate * image_duration)

    for idx, image in enumerate(images):
        # Check if image sizes are consistent
        if image.shape[0] != height or image.shape[1] != width:
            raise ValueError(f"Image size does not match the first image size")

        frame = image
        # Zoom the image a little bit to make it look like a video
        for i in range(frame_count):
            # Here it should crop x pixels and then resize the image to the original size
            #frame = frame[zoom_variable:-zoom_variable, zoom_variable:-zoom_variable]
            #frame = cv2.resize(frame, (width, height))
            #cv2.imwrite(f"./data/{idx},{i}frame.jpg", frame)
            out.write(frame)

    out.release()
    
    ## Adding audio to the video
    video_clip = VideoFileClip(path)
    start_time = max(0, video_clip.duration - audio.duration)  # Ensure start_time is not negative
    # Create a new subclip from the video_clip starting from start_time to the end
    new_video_clip = video_clip.subclip(start_time, video_clip.duration)
    # Now, you can set the audio of the new_video_clip to final_audio
    final_clip = new_video_clip.set_audio(audio)

    # Write the result to a file
    os.remove(path)
    final_clip.write_videofile(path, codec='libx264', audio_codec='aac')


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
        audio_clip = CompositeAudioClip([audio_clip, music_clip.volumex(0.25)])  # Adjust volume of music as needed

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
