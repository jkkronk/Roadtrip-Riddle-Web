import os
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip, AudioClip, concatenate_audioclips, clips_array, CompositeAudioClip

def crop_to_aspect_ratio(image, size):
    """
    Crops the image to the aspect ratio of the size and then resizes it to the desired size
    
    Args:
        image: numpy array of the image
        size: tuple of (width, height) for desired output size
    
    Returns:
        Cropped and resized image
    """
    target_width, target_height = size
    target_ratio = target_width / target_height
    
    # Get current image dimensions
    height, width = image.shape[:2]
    current_ratio = width / height
    
    # Calculate dimensions for cropping
    if current_ratio > target_ratio:
        # Image is too wide - crop width
        new_width = int(height * target_ratio)
        crop_x = (width - new_width) // 2
        cropped = image[:, crop_x:crop_x + new_width]
    else:
        # Image is too tall - crop height
        new_height = int(width / target_ratio)
        crop_y = (height - new_height) // 2
        cropped = image[crop_y:crop_y + new_height, :]
    
    # Resize to final dimensions
    resized = cv2.resize(cropped, size)
    return resized

import os
import cv2
import numpy as np

def images_to_video(frame_folder, frame_folder_second, out_folder="data/videos/", 
                    frame_rate=24, 
                    video_codec=cv2.VideoWriter_fourcc(*'avc1'), 
                    size=(1080, 1920)):
    """
    Creates a video from two folders of images by stacking the second folder's image 
    under the first folder's image for each frame.
    
    :param frame_folder: path to the folder containing the first set of images
    :param frame_folder_second: path to the folder containing the second set of images
    :param out_folder: path to the output folder
    :param frame_rate: frames per second
    :param video_codec: what codec to use for the video
    :param size: size of the single image in the output (width, height)
                 The final output video will have double the height if we're stacking images.
    :return:
    """
    # Get sorted list of image filenames from the first folder
    filenames = [f for f in os.listdir(frame_folder) if f.lower().endswith((".jpg", ".jpeg"))]
    # Modified sorting to handle filenames without underscores
    sorted_filenames = sorted(filenames, key=lambda x: int(''.join(filter(str.isdigit, x.split('.')[0])) or 0))

    # Get sorted list of image filenames from the second folder
    if frame_folder_second is not None:
        filenames_second = [f for f in os.listdir(frame_folder_second) if f.lower().endswith((".png"))]
        sorted_filenames_second = sorted(filenames_second, key=lambda x: int(''.join(filter(str.isdigit, x.split('.')[0])) or 0))
    else:
        sorted_filenames_second = []

    if not sorted_filenames:
        raise ValueError("No images found in the first folder")
    if frame_folder_second is not None and not sorted_filenames_second:
        raise ValueError("No images found in the second folder")

    if frame_folder_second is not None and len(sorted_filenames) != len(sorted_filenames_second):
        raise ValueError("The number of images in both folders must be the same")

    # Read the first pair of images to determine final video size
    first_image_top = cv2.imread(os.path.join(frame_folder, sorted_filenames[0]))
    if frame_folder_second is not None:
        first_image_bottom = cv2.imread(os.path.join(frame_folder_second, sorted_filenames_second[0]))
    else:
        first_image_bottom = None

    # Assuming you have a function crop_to_aspect_ratio that crops images to the given size
    top_cropped = crop_to_aspect_ratio(first_image_top, size)
    if frame_folder_second is not None:
        bottom_cropped = crop_to_aspect_ratio(first_image_bottom, size)
    else:
        bottom_cropped = None

    # Check if sizes match
    if top_cropped.shape[1] != size[0] or top_cropped.shape[0] != size[1]:
        raise ValueError(f"Top image size after cropping does not match the desired {size}")
    if bottom_cropped is not None and (bottom_cropped.shape[1] != size[0] or bottom_cropped.shape[0] != size[1]):
        raise ValueError(f"Bottom image size after cropping does not match the desired {size}")

    # Define the final size to stack one image under the other
    if frame_folder_second is not None:
        final_size = (size[0], size[1]*2)  # same width, double height
    else:
        final_size = size

    # Create VideoWriter object
    out = cv2.VideoWriter(os.path.join(out_folder, "quiz_no_audio.mp4"), video_codec, frame_rate, final_size)

    for idx in range(len(sorted_filenames)):
        # Read and preprocess top image
        frame_top = cv2.imread(os.path.join(frame_folder, sorted_filenames[idx]))
        frame_top = crop_to_aspect_ratio(frame_top, size)
        if frame_top.shape[1] != size[0] or frame_top.shape[0] != size[1]:
            raise ValueError(f"Image size for {sorted_filenames[idx]} does not match the set image size")

        # Read and preprocess bottom image
        if frame_folder_second is not None:
            frame_bottom = cv2.imread(os.path.join(frame_folder_second, sorted_filenames_second[idx]))
            frame_bottom = crop_to_aspect_ratio(frame_bottom, size)
            if frame_bottom.shape[1] != size[0] or frame_bottom.shape[0] != size[1]:
                raise ValueError(f"Image size for {sorted_filenames_second[idx]} does not match the set image size")

        # Stack images vertically
        if frame_folder_second is not None:
            combined_frame = np.vstack((frame_top, frame_bottom))
        else:
            combined_frame = frame_top
        
        # Write combined frame to video
        out.write(combined_frame)

    out.release()
    print("Video created successfully at:", os.path.join(out_folder, "quiz_no_audio.mp4"))



def create_new_video(video_clip, audio_clip, out_dir="./data/videos/"):
    """
    Creates a new video from the images in the data_dir
    :param video_clip: video clip
    :param audio_clip: audio clip
    :param out_dir: path to the output directory
    :return:
    """
    audio_duration = audio_clip.duration  # Get the final audio duration
    video_duration = video_clip.duration  # Get the original video duration

    # Calculate the start time for the new subclip to match the audio duration
    start_time = max(0, video_duration - audio_duration)  # Ensure start_time is not negative
    # Create a new subclip from the video_clip starting from start_time to the end
    new_video_clip = video_clip.subclip(start_time, video_duration)
    # Now, you can set the audio of the new_video_clip to final_audio
    final_clip = new_video_clip.set_audio(audio_clip)

    # Write the result to a file
    final_clip.write_videofile(os.path.join(out_dir, "quiz.mp4"), codec='libx264', audio_codec='aac')
